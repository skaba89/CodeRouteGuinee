#!/usr/bin/env python3
"""Verify that a public CodeRoute Render runtime serves the expected Git SHA.

Read-only and credential-free: the script calls only /health/live and
/health/readiness, compares Render's RENDER_GIT_COMMIT fingerprint exposed by the
API with an expected full SHA, and can persist a privacy-safe JSON receipt.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

_SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
DEFAULT_TIMEOUT_SECONDS = 15.0


def utc_now() -> datetime:
    return datetime.now(UTC)


def safe_base_url(raw: str, *, allow_http: bool = False) -> str:
    value = (raw or "").strip().rstrip("/")
    if not value:
        raise ValueError("base URL absente")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("base URL invalide")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("base URL ne doit contenir ni credential, query string ni fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("base URL doit pointer vers la racine du backend")
    if parsed.scheme == "http" and not allow_http and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("HTTP non chiffré refusé hors localhost")
    return value


def _origin(raw: str) -> str:
    parsed = urlparse(raw)
    port = f":{parsed.port}" if parsed.port else ""
    return urlunparse((parsed.scheme, f"{parsed.hostname}{port}", "", "", "", ""))


def request_json(base_url: str, path: str, timeout: float) -> tuple[int | None, dict[str, Any] | None, str | None]:
    request = Request(
        urljoin(base_url + "/", path.lstrip("/")),
        headers={"Accept": "application/json", "User-Agent": "CodeRoute-Render-Fingerprint/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - validated operator URL
            status_code = int(getattr(response, "status", response.getcode()))
            raw = response.read(500_000)
            content_type = str(response.headers.get("content-type", ""))
        if "json" not in content_type.lower():
            return status_code, None, "unexpected non-JSON response"
        decoded = json.loads(raw.decode("utf-8"))
        if not isinstance(decoded, dict):
            return status_code, None, "JSON response is not an object"
        return status_code, decoded, None
    except HTTPError as exc:
        return int(exc.code), None, f"HTTP {int(exc.code)}"
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, None, exc.__class__.__name__


def evaluate_runtime(
    live: dict[str, Any] | None,
    readiness: dict[str, Any] | None,
    *,
    expected_commit: str,
    expected_repo_slug: str | None = None,
) -> dict[str, Any]:
    if not _SHA40.fullmatch(expected_commit or ""):
        raise ValueError("expected_commit doit être un SHA Git complet de 40 caractères hexadécimaux")

    live = live or {}
    readiness = readiness or {}
    runtime = live.get("runtime") if isinstance(live.get("runtime"), dict) else {}
    actual_commit = str(runtime.get("git_commit") or "").strip()
    actual_repo = str(runtime.get("git_repo_slug") or "").strip()
    actual_branch = str(runtime.get("git_branch") or "").strip()

    checks = [
        {
            "code": "LIVENESS_OK",
            "passed": live.get("status") == "ok",
            "detail": f"health.live={live.get('status') or 'unknown'}",
        },
        {
            "code": "READINESS_OK",
            "passed": readiness.get("status") == "ready",
            "detail": f"health.readiness={readiness.get('status') or 'unknown'}",
        },
        {
            "code": "RENDER_GIT_COMMIT_PRESENT",
            "passed": bool(_SHA40.fullmatch(actual_commit)),
            "detail": f"git_commit={actual_commit or 'missing'}",
        },
        {
            "code": "DEPLOYED_SHA_MATCH",
            "passed": actual_commit.lower() == expected_commit.lower(),
            "detail": f"deployed={actual_commit or 'missing'} expected={expected_commit}",
        },
    ]
    if expected_repo_slug:
        checks.append(
            {
                "code": "REPOSITORY_MATCH",
                "passed": actual_repo.lower() == expected_repo_slug.strip().lower(),
                "detail": f"repo={actual_repo or 'missing'} expected={expected_repo_slug}",
            }
        )

    blockers = [item["code"] for item in checks if not item["passed"]]
    return {
        "passed": not blockers,
        "expected_commit": expected_commit.lower(),
        "deployed_commit": actual_commit.lower() or None,
        "git_branch": actual_branch or None,
        "git_repo_slug": actual_repo or None,
        "render_service_name": runtime.get("render_service_name"),
        "render_instance_id": runtime.get("render_instance_id"),
        "checks": checks,
        "blockers": blockers,
    }


def build_receipt(
    *,
    base_url: str,
    expected_commit: str,
    expected_repo_slug: str | None,
    timeout: float,
) -> dict[str, Any]:
    live_status, live, live_error = request_json(base_url, "/health/live", timeout)
    ready_status, readiness, ready_error = request_json(base_url, "/health/readiness", timeout)
    assessment = evaluate_runtime(
        live,
        readiness,
        expected_commit=expected_commit,
        expected_repo_slug=expected_repo_slug,
    )
    if live_status is None or not (200 <= live_status < 300):
        assessment["passed"] = False
        assessment["blockers"] = sorted(set(assessment["blockers"] + ["LIVENESS_HTTP_2XX"]))
    if ready_status is None or not (200 <= ready_status < 300):
        assessment["passed"] = False
        assessment["blockers"] = sorted(set(assessment["blockers"] + ["READINESS_HTTP_2XX"]))

    return {
        "schema": "coderoute_render_deployment_receipt_v1",
        "generated_at": utc_now().isoformat(),
        "target_origin": _origin(base_url),
        "http": {
            "health_live": {"status_code": live_status, "error": live_error},
            "health_readiness": {"status_code": ready_status, "error": ready_error},
        },
        "assessment": assessment,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the Git SHA currently served by CodeRoute on Render")
    parser.add_argument("--base-url", default=os.getenv("CODEROUTE_API_BASE_URL", ""))
    parser.add_argument("--expected-commit", default=os.getenv("CODEROUTE_EXPECTED_GIT_COMMIT", os.getenv("GITHUB_SHA", "")))
    parser.add_argument("--expected-repo-slug", default=os.getenv("CODEROUTE_EXPECTED_REPO_SLUG", "skaba89/CodeRouteGuinee"))
    parser.add_argument("--receipt", default="")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--allow-http", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0 or args.timeout > 120:
        print("ERROR: --timeout doit être > 0 et <= 120 secondes", file=sys.stderr)
        return 2
    try:
        base_url = safe_base_url(args.base_url, allow_http=bool(args.allow_http))
        if not _SHA40.fullmatch((args.expected_commit or "").strip()):
            raise ValueError("--expected-commit doit être un SHA Git complet de 40 caractères")
        receipt = build_receipt(
            base_url=base_url,
            expected_commit=args.expected_commit.strip(),
            expected_repo_slug=(args.expected_repo_slug or "").strip() or None,
            timeout=float(args.timeout),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.receipt:
        path = Path(args.receipt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["assessment"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

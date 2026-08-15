#!/usr/bin/env python3
"""Verify that a public CodeRoute Render runtime serves the expected Git SHA.

Read-only and credential-free: the script calls only /health/live and
/health/readiness, compares Render's RENDER_GIT_COMMIT fingerprint exposed by the
API with an expected full SHA, and can persist a privacy-safe JSON receipt.

Transient network failures are retried with a bounded policy. Permanent client
errors remain fail-fast and a persistent outage still fails the verification.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

_SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
_SAFE_CHECK_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 2.0
RETRYABLE_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


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


def _decode_json_object(raw: bytes, content_type: str) -> dict[str, Any] | None:
    if "json" not in content_type.lower():
        return None
    decoded = json.loads(raw.decode("utf-8"))
    return decoded if isinstance(decoded, dict) else None


def request_json(base_url: str, path: str, timeout: float) -> tuple[int | None, dict[str, Any] | None, str | None]:
    """Perform one read-only JSON request.

    JSON error bodies are preserved for diagnostics. This is particularly useful
    for ``/health/readiness`` where a deliberate HTTP 503 still carries a
    privacy-safe body describing which readiness checks are blocking.

    Retry orchestration intentionally lives in ``request_json_with_retry`` so
    this primitive stays deterministic and easy to test.
    """
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
        decoded = _decode_json_object(raw, content_type)
        if decoded is None:
            return status_code, None, "JSON response is not an object"
        return status_code, decoded, None
    except HTTPError as exc:
        status_code = int(exc.code)
        try:
            raw = exc.read(500_000)
            content_type = str(exc.headers.get("content-type", "")) if exc.headers else ""
            decoded = _decode_json_object(raw, content_type)
            if decoded is not None:
                return status_code, decoded, f"HTTP {status_code}"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        return status_code, None, f"HTTP {status_code}"
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, None, exc.__class__.__name__


def _is_retryable(status_code: int | None) -> bool:
    return status_code is None or status_code in RETRYABLE_HTTP_STATUSES


def request_json_with_retry(
    base_url: str,
    path: str,
    timeout: float,
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[int | None, dict[str, Any] | None, str | None, int]:
    """Request JSON with bounded retries for transient failures only.

    Returns the final HTTP status/payload/error plus the number of attempts used.
    A permanent 4xx fails immediately; network errors and selected transient HTTP
    statuses are retried until ``attempts`` is exhausted.
    """
    if attempts < 1:
        raise ValueError("attempts doit être >= 1")
    if retry_delay < 0:
        raise ValueError("retry_delay doit être >= 0")

    last_status: int | None = None
    last_payload: dict[str, Any] | None = None
    last_error: str | None = None

    for attempt_number in range(1, attempts + 1):
        last_status, last_payload, last_error = request_json(base_url, path, timeout)
        if not _is_retryable(last_status) or attempt_number == attempts:
            return last_status, last_payload, last_error, attempt_number
        if retry_delay > 0:
            sleep_fn(retry_delay)

    return last_status, last_payload, last_error, attempts


def _health_http_summary(
    status_code: int | None,
    payload: dict[str, Any] | None,
    error: str | None,
    attempts_used: int,
) -> dict[str, Any]:
    """Return only privacy-safe diagnostics from a public health payload."""
    summary: dict[str, Any] = {
        "status_code": status_code,
        "error": error,
        "attempts_used": attempts_used,
    }
    if not isinstance(payload, dict):
        return summary

    reported_status = payload.get("status")
    if isinstance(reported_status, str) and len(reported_status) <= 40:
        summary["reported_status"] = reported_status

    blockers = payload.get("blocking_checks")
    if isinstance(blockers, list):
        safe_blockers = [
            item for item in blockers
            if isinstance(item, str) and _SAFE_CHECK_NAME.fullmatch(item)
        ]
        summary["blocking_checks"] = safe_blockers[:20]
    return summary


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
    attempts: int = DEFAULT_ATTEMPTS,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict[str, Any]:
    live_status, live, live_error, live_attempts = request_json_with_retry(
        base_url,
        "/health/live",
        timeout,
        attempts=attempts,
        retry_delay=retry_delay,
    )
    ready_status, readiness, ready_error, ready_attempts = request_json_with_retry(
        base_url,
        "/health/readiness",
        timeout,
        attempts=attempts,
        retry_delay=retry_delay,
    )
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
        "retry_policy": {
            "attempts": attempts,
            "retry_delay_seconds": retry_delay,
            "retryable_http_statuses": sorted(RETRYABLE_HTTP_STATUSES),
        },
        "http": {
            "health_live": _health_http_summary(live_status, live, live_error, live_attempts),
            "health_readiness": _health_http_summary(ready_status, readiness, ready_error, ready_attempts),
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
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument("--retry-delay", type=float, default=DEFAULT_RETRY_DELAY_SECONDS)
    parser.add_argument("--allow-http", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0 or args.timeout > 120:
        print("ERROR: --timeout doit être > 0 et <= 120 secondes", file=sys.stderr)
        return 2
    if args.attempts < 1 or args.attempts > 10:
        print("ERROR: --attempts doit être compris entre 1 et 10", file=sys.stderr)
        return 2
    if args.retry_delay < 0 or args.retry_delay > 30:
        print("ERROR: --retry-delay doit être compris entre 0 et 30 secondes", file=sys.stderr)
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
            attempts=int(args.attempts),
            retry_delay=float(args.retry_delay),
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

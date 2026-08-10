#!/usr/bin/env python3
"""Verify that the public Render frontend serves the Guinea exam media pack.

Read-only and credential-free. The script validates the generated demo manifest,
fetches every declared asset, checks content type/magic bytes/size, and writes a
privacy-safe deployment receipt. It does not infer DNTT approval.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

DEFAULT_FRONTEND_URL = "https://coderouteguinee-frontend.onrender.com"
DEFAULT_MANIFEST_PATH = "/media/exam/guinea/manifest.json"
DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_ASSET_BYTES = 2_500_000


def utc_now() -> datetime:
    return datetime.now(UTC)


def safe_base_url(raw: str, *, allow_http: bool = False) -> str:
    value = (raw or "").strip().rstrip("/")
    if not value:
        raise ValueError("frontend URL absente")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("frontend URL invalide")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("frontend URL ne doit contenir ni credential, query string ni fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("frontend URL doit pointer vers la racine du site")
    if parsed.scheme == "http" and not allow_http and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("HTTP non chiffré refusé hors localhost")
    return value


def _origin(raw: str) -> str:
    parsed = urlparse(raw)
    port = f":{parsed.port}" if parsed.port else ""
    return urlunparse((parsed.scheme, f"{parsed.hostname}{port}", "", "", "", ""))


def request_bytes(base_url: str, path: str, timeout: float, *, max_bytes: int) -> tuple[int | None, bytes | None, str, str | None]:
    request = Request(
        urljoin(base_url + "/", path.lstrip("/")),
        headers={"Accept": "*/*", "User-Agent": "CodeRoute-Media-Deployment/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - validated operator URL
            status_code = int(getattr(response, "status", response.getcode()))
            content_type = str(response.headers.get("content-type", ""))
            raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            return status_code, None, content_type, "response_too_large"
        return status_code, raw, content_type, None
    except HTTPError as exc:
        return int(exc.code), None, str(exc.headers.get("content-type", "")), f"HTTP {int(exc.code)}"
    except (URLError, TimeoutError, OSError) as exc:
        return None, None, "", exc.__class__.__name__


def _manifest_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    governance = manifest.get("governance") if isinstance(manifest.get("governance"), dict) else {}
    assets = manifest.get("assets") if isinstance(manifest.get("assets"), list) else []
    return [
        {"code": "MANIFEST_SCHEMA_V1", "passed": manifest.get("schema_version") == 1},
        {"code": "DEMO_GENERATED_DECLARED", "passed": governance.get("source_type") == "generated"},
        {"code": "DEMO_NOT_OFFICIAL", "passed": governance.get("quality_status") == "DEMO_NOT_OFFICIAL"},
        {"code": "REGULATORY_NOT_REVIEWED", "passed": governance.get("regulatory_status") == "NOT_REVIEWED"},
        {"code": "OFFICIAL_EXAM_FORBIDDEN", "passed": governance.get("official_exam_allowed") is False},
        {"code": "ASSET_LIST_PRESENT", "passed": len(assets) >= 4},
    ]


def evaluate_asset(item: dict[str, Any], *, status_code: int | None, raw: bytes | None, content_type: str, error: str | None) -> dict[str, Any]:
    filename = str(item.get("file") or "")
    kind = str(item.get("kind") or "")
    http_ok = status_code is not None and 200 <= status_code < 300 and raw is not None and error is None
    magic_ok = False
    content_type_ok = False
    if http_ok and raw is not None:
        if kind == "image":
            magic_ok = len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
            content_type_ok = "image/webp" in content_type.lower()
        elif kind == "video":
            magic_ok = b"ftyp" in raw[:32]
            content_type_ok = "video/mp4" in content_type.lower() or "application/mp4" in content_type.lower()

    checks = [
        {"code": "HTTP_2XX", "passed": bool(http_ok)},
        {"code": "CONTENT_TYPE", "passed": bool(content_type_ok)},
        {"code": "MAGIC_BYTES", "passed": bool(magic_ok)},
        {"code": "MOBILE_SIZE_BUDGET", "passed": bool(raw is not None and len(raw) <= MAX_ASSET_BYTES)},
    ]
    if kind == "video":
        duration = item.get("duration_seconds")
        checks.extend([
            {"code": "VIDEO_DURATION_6_20", "passed": isinstance(duration, int | float) and 6 <= float(duration) <= 20},
            {"code": "VIDEO_POSTER_DECLARED", "passed": bool(item.get("poster"))},
            {"code": "VIDEO_FALLBACK_DECLARED", "passed": bool(item.get("fallback"))},
        ])
    blockers = [check["code"] for check in checks if not check["passed"]]
    return {
        "file": filename,
        "kind": kind,
        "passed": not blockers,
        "status_code": status_code,
        "content_type": content_type or None,
        "bytes": len(raw) if raw is not None else None,
        "error": error,
        "checks": checks,
        "blockers": blockers,
    }


def build_receipt(*, frontend_url: str, manifest_path: str, timeout: float) -> dict[str, Any]:
    status, raw, content_type, error = request_bytes(
        frontend_url,
        manifest_path,
        timeout,
        max_bytes=500_000,
    )
    manifest: dict[str, Any] = {}
    manifest_error = error
    if raw is not None:
        try:
            decoded = json.loads(raw.decode("utf-8"))
            if isinstance(decoded, dict):
                manifest = decoded
            else:
                manifest_error = "manifest_not_object"
        except (UnicodeDecodeError, json.JSONDecodeError):
            manifest_error = "manifest_invalid_json"

    checks = _manifest_checks(manifest)
    checks.insert(0, {"code": "MANIFEST_HTTP_2XX", "passed": status is not None and 200 <= status < 300})
    checks.insert(1, {"code": "MANIFEST_JSON", "passed": bool(manifest) and manifest_error is None and "json" in content_type.lower()})

    asset_results: list[dict[str, Any]] = []
    for item in manifest.get("assets", []) if isinstance(manifest.get("assets"), list) else []:
        if not isinstance(item, dict) or not str(item.get("file") or "").strip():
            asset_results.append({"file": None, "passed": False, "blockers": ["INVALID_MANIFEST_ITEM"]})
            continue
        asset_status, asset_raw, asset_type, asset_error = request_bytes(
            frontend_url,
            f"/media/exam/guinea/{item['file']}",
            timeout,
            max_bytes=MAX_ASSET_BYTES,
        )
        asset_results.append(
            evaluate_asset(
                item,
                status_code=asset_status,
                raw=asset_raw,
                content_type=asset_type,
                error=asset_error,
            )
        )

    blockers = [check["code"] for check in checks if not check["passed"]]
    if any(not item.get("passed", False) for item in asset_results):
        blockers.append("MEDIA_ASSET_DELIVERY")

    return {
        "schema": "coderoute_media_deployment_receipt_v1",
        "generated_at": utc_now().isoformat(),
        "target_origin": _origin(frontend_url),
        "manifest_path": manifest_path,
        "passed": not blockers,
        "checks": checks,
        "assets": asset_results,
        "blockers": sorted(set(blockers)),
        "institutional_validation_inferred": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify CodeRoute Guinea media served by the public frontend")
    parser.add_argument("--frontend-url", default=os.getenv("CODEROUTE_FRONTEND_BASE_URL", DEFAULT_FRONTEND_URL))
    parser.add_argument("--manifest-path", default=DEFAULT_MANIFEST_PATH)
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
        frontend_url = safe_base_url(args.frontend_url, allow_http=bool(args.allow_http))
        if not str(args.manifest_path).startswith("/") or ".." in str(args.manifest_path):
            raise ValueError("--manifest-path invalide")
        receipt = build_receipt(
            frontend_url=frontend_url,
            manifest_path=str(args.manifest_path),
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
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

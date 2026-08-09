#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx


def _payload(receipt: dict) -> dict:
    kind = receipt.get("kind")
    if kind == "coderoute_offsite_backup_receipt_v2":
        return {
            "kind": "backup_uploaded",
            "occurred_at": receipt["uploaded_at"],
            "artifact_sha256": receipt["bundle_sha256"],
            "region": receipt.get("target_region"),
            "reference": receipt.get("object_key"),
        }
    if kind == "coderoute_restore_drill_receipt_v1":
        return {
            "kind": "restore_drill_passed",
            "occurred_at": receipt["verified_at"],
            "artifact_sha256": receipt.get("dump_sha256"),
        }
    if kind == "coderoute_ha_failover_probe_receipt_v1":
        return {
            "kind": "ha_failover_probe_passed",
            "occurred_at": receipt["finished_at"],
            "availability_percent": receipt.get("availability_percent"),
            "duration_seconds": receipt.get("duration_seconds"),
        }
    raise SystemExit(f"type de reçu non supporté: {kind!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    args = parser.parse_args()

    base = os.getenv("CODEROUTE_API_BASE_URL", "").rstrip("/")
    token = os.getenv("RELIABILITY_EVIDENCE_TOKEN", "").strip()
    if not base or not token:
        raise SystemExit("CODEROUTE_API_BASE_URL et RELIABILITY_EVIDENCE_TOKEN sont obligatoires")
    parsed = urlparse(base)
    allow_insecure = os.getenv("ALLOW_INSECURE_RELIABILITY_API", "false").lower() == "true"
    if parsed.scheme != "https" and not allow_insecure:
        raise SystemExit("CODEROUTE_API_BASE_URL doit utiliser HTTPS")
    if parsed.username or parsed.password:
        raise SystemExit("CODEROUTE_API_BASE_URL ne doit contenir aucun credential")

    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    payload = _payload(receipt)
    with httpx.Client(timeout=15.0, follow_redirects=False) as client:
        response = client.post(
            f"{base}/api/v1/operations/reliability/evidence",
            headers={"X-Reliability-Evidence-Token": token, "Content-Type": "application/json"},
            json=payload,
        )
    if response.status_code != 201:
        raise SystemExit(f"publication preuve reliability refusée: HTTP {response.status_code}")
    print(json.dumps(response.json(), sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Mesure la continuité API pendant une perte/reprise d'instance pilotée à l'extérieur.

Ce script ne tue aucune instance. L'opérateur déclenche le failover via son
orchestrateur pendant que la sonde mesure `/health/live` et produit un reçu.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx


def summarize(samples: list[dict], *, started_at: datetime, finished_at: datetime) -> dict:
    total = len(samples)
    successes = sum(1 for item in samples if item["ok"])
    availability = round((successes / total) * 100.0, 4) if total else 0.0
    latencies = sorted(float(item["latency_ms"]) for item in samples if item["ok"])
    if latencies:
        index = max(0, math.ceil(0.95 * len(latencies)) - 1)
        p95 = round(latencies[index], 2)
    else:
        p95 = None

    longest = 0
    current = 0
    for item in samples:
        if item["ok"]:
            current = 0
        else:
            current += 1
            longest = max(longest, current)

    return {
        "kind": "coderoute_ha_failover_probe_receipt_v1",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "requests_total": total,
        "requests_success": successes,
        "requests_failed": total - successes,
        "availability_percent": availability,
        "p95_latency_ms": p95,
        "max_consecutive_failures": longest,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--duration-seconds", type=float, default=120.0)
    parser.add_argument("--interval-seconds", type=float, default=0.5)
    parser.add_argument("--min-availability", type=float, default=99.0)
    parser.add_argument("--max-consecutive-failures", type=int, default=2)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise SystemExit("base_url doit utiliser HTTPS hors laboratoire local")
    if args.duration_seconds <= 0 or args.interval_seconds <= 0:
        raise SystemExit("durée/intervalle invalides")

    samples: list[dict] = []
    started = datetime.now(UTC)
    deadline = time.monotonic() + args.duration_seconds
    with httpx.Client(timeout=min(5.0, max(1.0, args.interval_seconds * 4)), follow_redirects=False) as client:
        while time.monotonic() < deadline:
            tick = time.monotonic()
            ok = False
            status_code = None
            try:
                response = client.get(f"{base}/health/live")
                status_code = response.status_code
                ok = status_code == 200 and response.json().get("status") == "ok"
            except Exception:
                ok = False
            latency_ms = (time.monotonic() - tick) * 1000.0
            samples.append({"ok": ok, "status_code": status_code, "latency_ms": latency_ms})
            sleep_for = args.interval_seconds - (time.monotonic() - tick)
            if sleep_for > 0:
                time.sleep(sleep_for)

    finished = datetime.now(UTC)
    receipt = summarize(samples, started_at=started, finished_at=finished)
    receipt["thresholds"] = {
        "min_availability_percent": args.min_availability,
        "max_consecutive_failures": args.max_consecutive_failures,
    }
    receipt["passed"] = (
        receipt["availability_percent"] >= args.min_availability
        and receipt["max_consecutive_failures"] <= args.max_consecutive_failures
    )

    path = Path(args.receipt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    path.chmod(0o600)
    print(json.dumps(receipt, sort_keys=True))
    if not receipt["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

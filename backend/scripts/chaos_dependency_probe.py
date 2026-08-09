#!/usr/bin/env python3
"""Probe passif P11 pendant un chaos contrôlé exécuté par un opérateur.

Ce script ne coupe aucun service. Il mesure seulement liveness/readiness pendant
qu'un opérateur retire une instance, coupe Redis ou simule une dépendance.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx


def _validate_base_url(value: str, allow_insecure: bool) -> str:
    base = value.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in ({"https", "http"} if allow_insecure else {"https"}):
        raise SystemExit("BASE_URL doit utiliser HTTPS (HTTP uniquement avec --allow-insecure-lab)")
    if parsed.username or parsed.password:
        raise SystemExit("BASE_URL ne doit contenir aucun credential")
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--scenario", choices=["api-instance-loss", "redis-loss", "database-loss"], required=True)
    parser.add_argument("--allow-insecure-lab", action="store_true")
    parser.add_argument("--output", default="chaos-probe-receipt.json")
    args = parser.parse_args()

    if args.duration_seconds < 10 or args.duration_seconds > 3600:
        raise SystemExit("duration-seconds doit être compris entre 10 et 3600")
    base = _validate_base_url(args.base_url, args.allow_insecure_lab)
    started = datetime.now(UTC)
    deadline = time.monotonic() + args.duration_seconds
    live_ok = 0
    ready_ok = 0
    samples = 0
    latencies: list[float] = []
    observations: list[dict] = []

    with httpx.Client(timeout=5.0, follow_redirects=False) as client:
        while time.monotonic() < deadline:
            sample: dict = {"at": datetime.now(UTC).isoformat()}
            for label, path in (("live", "/health/live"), ("ready", "/health/readiness")):
                t0 = time.perf_counter()
                try:
                    response = client.get(f"{base}{path}")
                    latency_ms = (time.perf_counter() - t0) * 1000
                    ok = response.status_code == 200
                    sample[label] = {"status": response.status_code, "ok": ok, "latency_ms": round(latency_ms, 1)}
                    if label == "live" and ok:
                        live_ok += 1
                    if label == "ready" and ok:
                        ready_ok += 1
                    latencies.append(latency_ms)
                except Exception as exc:
                    sample[label] = {"status": None, "ok": False, "error_type": exc.__class__.__name__}
            observations.append(sample)
            samples += 1
            time.sleep(args.interval_seconds)

    finished = datetime.now(UTC)
    live_pct = (100.0 * live_ok / samples) if samples else 0.0
    ready_pct = (100.0 * ready_ok / samples) if samples else 0.0
    p95_ms = 0.0
    if latencies:
        ordered = sorted(latencies)
        p95_ms = ordered[min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))]

    if args.scenario == "api-instance-loss":
        passed = live_pct >= 99.0 and ready_pct >= 99.0
    elif args.scenario == "redis-loss":
        # P10 garantit que Redis est reconstructible et ne doit pas retirer les API.
        passed = live_pct >= 99.0 and ready_pct >= 99.0
    else:
        # Une perte DB doit conserver la liveness mais rendre readiness non prête.
        passed = live_pct >= 99.0 and ready_pct <= 20.0

    receipt = {
        "kind": "coderoute_chaos_dependency_probe_v1",
        "scenario": args.scenario,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "samples": samples,
        "liveness_percent": round(live_pct, 3),
        "readiness_percent": round(ready_pct, 3),
        "p95_latency_ms": round(p95_ms, 1),
        "passed": passed,
        "observations": observations[-120:],
    }
    from pathlib import Path
    Path(args.output).write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k != "observations"}, sort_keys=True))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()

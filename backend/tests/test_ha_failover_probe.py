from datetime import UTC, datetime, timedelta

from scripts.ha_failover_probe import summarize


def test_failover_summary_calculates_availability_p95_and_outage_run() -> None:
    started = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)
    finished = started + timedelta(seconds=10)
    samples = [
        {"ok": True, "latency_ms": 80.0},
        {"ok": True, "latency_ms": 100.0},
        {"ok": False, "latency_ms": 5000.0},
        {"ok": False, "latency_ms": 5000.0},
        {"ok": True, "latency_ms": 120.0},
        {"ok": True, "latency_ms": 300.0},
        {"ok": True, "latency_ms": 110.0},
        {"ok": True, "latency_ms": 90.0},
        {"ok": True, "latency_ms": 95.0},
        {"ok": True, "latency_ms": 105.0},
    ]

    receipt = summarize(samples, started_at=started, finished_at=finished)
    assert receipt["kind"] == "coderoute_ha_failover_probe_receipt_v1"
    assert receipt["requests_total"] == 10
    assert receipt["requests_success"] == 8
    assert receipt["requests_failed"] == 2
    assert receipt["availability_percent"] == 80.0
    assert receipt["p95_latency_ms"] == 300.0
    assert receipt["max_consecutive_failures"] == 2


def test_failover_summary_handles_total_outage() -> None:
    now = datetime.now(UTC)
    receipt = summarize(
        [{"ok": False, "latency_ms": 1000.0}] * 4,
        started_at=now,
        finished_at=now + timedelta(seconds=2),
    )
    assert receipt["availability_percent"] == 0.0
    assert receipt["p95_latency_ms"] is None
    assert receipt["max_consecutive_failures"] == 4

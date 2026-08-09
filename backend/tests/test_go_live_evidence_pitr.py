from datetime import UTC, datetime

from scripts.collect_go_live_evidence import evaluate_snapshot


def _obs(body=None, *, ok=True):
    return {
        "ok": ok,
        "skipped": False,
        "status_code": 200 if ok else None,
        "error": None if ok else "test",
        "body": body,
    }


def _observations(*, pitr_time):
    now = datetime(2026, 8, 9, 18, 30, tzinfo=UTC)
    evidence_time = now.isoformat()
    return now, {
        "health_live": _obs({"status": "ok"}),
        "health_readiness": _obs({"status": "ready"}),
        "reliability": _obs(
            {
                "last_evidence": {
                    "backup_uploaded": evidence_time,
                    "restore_drill_passed": evidence_time,
                    "pitr_drill_passed": pitr_time,
                    "ha_failover_probe_passed": evidence_time,
                }
            }
        ),
        "security": _obs(
            {
                "status": "ok",
                "soc_policy": {"enabled": True, "audit_chain_enabled": True},
                "audit_chain": {"valid": True},
            }
        ),
        "governance_contract": _obs({"alignment": {"aligned": True}}),
        "governance_readiness": _obs({"go_live_allowed": True, "blockers": []}),
        "homologation_dossiers": _obs([]),
    }


def test_fresh_pitr_evidence_allows_automated_pack_to_pass():
    now, observations = _observations(pitr_time="2026-08-09T18:30:00+00:00")
    result = evaluate_snapshot(observations, now=now)
    assert result["status"] == "automated_checks_passed"
    pitr = next(item for item in result["checks"] if item["code"] == "P10_PITR_FRESH")
    assert pitr["passed"] is True
    assert result["institutional_homologation_claimed"] is False


def test_missing_pitr_evidence_is_explicit_blocker():
    now, observations = _observations(pitr_time=None)
    result = evaluate_snapshot(observations, now=now)
    assert result["status"] == "blocked"
    pitr = next(item for item in result["checks"] if item["code"] == "P10_PITR_FRESH")
    assert pitr["passed"] is False
    assert "aucune preuve horodatée" in pitr["detail"]


def test_stale_pitr_evidence_is_explicit_blocker():
    now, observations = _observations(pitr_time="2026-01-01T00:00:00+00:00")
    result = evaluate_snapshot(observations, now=now)
    assert result["status"] == "blocked"
    pitr = next(item for item in result["checks"] if item["code"] == "P10_PITR_FRESH")
    assert pitr["passed"] is False
    assert "preuve trop ancienne" in pitr["detail"]

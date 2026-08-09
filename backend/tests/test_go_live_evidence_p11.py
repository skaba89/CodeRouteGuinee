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


def _observations(*, security_go_live):
    now = datetime(2026, 8, 9, 19, 0, tzinfo=UTC)
    evidence_time = now.isoformat()
    return now, {
        "health_live": _obs({"status": "ok"}),
        "health_readiness": _obs({"status": "ready"}),
        "reliability": _obs({
            "last_evidence": {
                "backup_uploaded": evidence_time,
                "restore_drill_passed": evidence_time,
                "pitr_drill_passed": evidence_time,
                "ha_failover_probe_passed": evidence_time,
            }
        }),
        "security": _obs({
            "status": "ok",
            "soc_policy": {"enabled": True, "audit_chain_enabled": True},
            "audit_chain": {"valid": True},
            "go_live": security_go_live,
            "alerts": [],
        }),
        "governance_contract": _obs({"alignment": {"aligned": True}}),
        "governance_readiness": _obs({"go_live_allowed": True, "blockers": []}),
        "homologation_dossiers": _obs([]),
    }


def test_evidence_pack_passes_p11_only_when_security_go_live_gate_is_ready():
    now, observations = _observations(security_go_live={"ready": True, "blockers": []})
    result = evaluate_snapshot(observations, now=now)
    control = next(item for item in result["checks"] if item["code"] == "P11_SECURITY_GO_LIVE")
    assert control["passed"] is True
    assert result["status"] == "automated_checks_passed"
    assert result["institutional_homologation_claimed"] is False


def test_evidence_pack_blocks_when_waf_siem_or_otel_gate_is_not_ready():
    now, observations = _observations(
        security_go_live={
            "ready": False,
            "blockers": ["otel_enabled", "waf_enforced", "siem_enforced"],
        }
    )
    result = evaluate_snapshot(observations, now=now)
    control = next(item for item in result["checks"] if item["code"] == "P11_SECURITY_GO_LIVE")
    assert control["passed"] is False
    assert "otel_enabled" in control["detail"]
    assert "waf_enforced" in control["detail"]
    assert "siem_enforced" in control["detail"]
    assert result["status"] == "blocked"


def test_evidence_pack_fails_closed_when_security_go_live_contract_is_absent():
    now, observations = _observations(security_go_live=None)
    result = evaluate_snapshot(observations, now=now)
    control = next(item for item in result["checks"] if item["code"] == "P11_SECURITY_GO_LIVE")
    assert control["passed"] is False
    assert "gate P11 absent" in control["detail"]

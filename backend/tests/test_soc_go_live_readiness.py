from app.routers.security_operations import build_security_go_live_controls
from app.soc_config import SOCSettings


def _soc(**overrides) -> SOCSettings:
    values = {
        "enabled": True,
        "pseudonym_key": "p" * 40,
        "audit_chain_enabled": True,
        "audit_chain_hmac_key": "h" * 40,
        "audit_verify_interval_seconds": 900,
        "otel_traces_enabled": True,
        "otel_endpoint": "https://otel.internal.example/v1/traces",
        "otel_headers": "Authorization=redacted",
        "otel_service_name": "coderoute-api",
        "otel_sample_ratio": 0.05,
        "waf_required": True,
        "waf_provider": "institutional-edge",
        "siem_required": True,
    }
    values.update(overrides)
    return SOCSettings(**values)


def _by_code(result: dict, code: str) -> dict:
    return next(item for item in result["controls"] if item["code"] == code)


def test_security_go_live_controls_are_green_only_when_all_runtime_gates_are_enabled():
    result = build_security_go_live_controls(_soc(), {"valid": True}, [])
    assert result["ready"] is True
    assert result["blockers"] == []
    assert all(item["passed"] for item in result["controls"])
    assert result["external_evidence_still_required"]


def test_dormant_waf_siem_and_otel_are_explicit_blockers():
    result = build_security_go_live_controls(
        _soc(
            enabled=False,
            audit_chain_enabled=False,
            otel_traces_enabled=False,
            otel_endpoint="",
            waf_required=False,
            waf_provider="",
            siem_required=False,
        ),
        {"valid": True},
        [],
    )
    assert result["ready"] is False
    assert "soc_enabled" in result["blockers"]
    assert "audit_hmac_enabled" in result["blockers"]
    assert "audit_chain_valid" in result["blockers"]
    assert "otel_enabled" in result["blockers"]
    assert "waf_enforced" in result["blockers"]
    assert "siem_enforced" in result["blockers"]


def test_invalid_audit_or_active_security_signal_blocks_go_live():
    audit = build_security_go_live_controls(_soc(), {"valid": False}, [])
    assert audit["ready"] is False
    assert _by_code(audit, "audit_chain_valid")["passed"] is False

    alert = build_security_go_live_controls(
        _soc(),
        {"valid": True},
        [{"code": "SUSPICIOUS_DEVICE", "severity": "warning"}],
    )
    assert alert["ready"] is False
    assert _by_code(alert, "no_active_security_alert")["passed"] is False

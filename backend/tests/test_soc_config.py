import pytest

from app.soc_config import SOCSettings


def _settings(**overrides) -> SOCSettings:
    values = {
        "enabled": True,
        "pseudonym_key": "p" * 48,
        "audit_chain_enabled": True,
        "audit_chain_hmac_key": "a" * 48,
        "audit_verify_interval_seconds": 900,
        "otel_traces_enabled": True,
        "otel_endpoint": "https://otel.example.test",
        "otel_headers": "Authorization=Bearer-test",
        "otel_service_name": "coderoute-api",
        "otel_sample_ratio": 0.05,
        "waf_required": True,
        "waf_provider": "institutional-edge",
        "siem_required": True,
    }
    values.update(overrides)
    return SOCSettings(**values)


def test_hardened_soc_configuration_is_valid() -> None:
    settings = _settings()
    settings.validate(production=True)
    safe = settings.safe_policy()
    assert safe["enabled"] is True
    assert safe["otel"]["endpoint_configured"] is True
    assert safe["audit_verify_interval_seconds"] == 900
    assert "pseudonym_key" not in str(safe)
    assert "audit_chain_hmac_key" not in str(safe)
    assert "Authorization" not in str(safe)


def test_production_soc_requires_long_pseudonym_and_audit_keys() -> None:
    with pytest.raises(RuntimeError, match="SOC_PSEUDONYM_KEY"):
        _settings(pseudonym_key="short").validate(production=True)
    with pytest.raises(RuntimeError, match="AUDIT_CHAIN_HMAC_KEY"):
        _settings(audit_chain_hmac_key="short").validate(production=True)


def test_otel_requires_https_and_no_credentials_in_production() -> None:
    with pytest.raises(RuntimeError, match="HTTPS"):
        _settings(otel_endpoint="http://otel.example.test").validate(production=True)
    with pytest.raises(RuntimeError, match="credential"):
        _settings(otel_endpoint="https://user:password@otel.example.test").validate(production=True)


def test_audit_verify_interval_is_bounded() -> None:
    with pytest.raises(RuntimeError, match="AUDIT_VERIFY_INTERVAL_SECONDS"):
        _settings(audit_verify_interval_seconds=30).validate(production=True)
    with pytest.raises(RuntimeError, match="AUDIT_VERIFY_INTERVAL_SECONDS"):
        _settings(audit_verify_interval_seconds=100_000).validate(production=True)


def test_waf_provider_is_required_only_when_policy_requires_it() -> None:
    with pytest.raises(RuntimeError, match="WAF_PROVIDER"):
        _settings(waf_provider="").validate(production=True)
    _settings(waf_required=False, waf_provider="").validate(production=True)

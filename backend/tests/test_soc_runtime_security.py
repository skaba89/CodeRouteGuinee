from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_global_500_handler_uses_initialized_monitoring_client_without_raw_url() -> None:
    main = _text(BACKEND_ROOT / "app/main.py")
    assert "capture_monitoring_exception" in main
    assert "from app.sentry import capture_exception" not in main
    assert 'str(_req.url)' not in main
    assert '"route": route' in main
    assert '"request_id": request_id' in main


def test_sentry_user_context_ignores_email_and_pseudonymizes_user_id() -> None:
    monitoring = _text(BACKEND_ROOT / "app/monitoring.py")
    assert "del email" in monitoring
    assert 'pseudonymize(user_id, "usr")' in monitoring
    assert '"email": email' not in monitoring


def test_render_stages_soc_dormant_until_infrastructure_is_provisioned() -> None:
    render = _text(REPO_ROOT / "render.yaml")
    assert "key: SOC_ENABLED\n        value: \"false\"" in render
    assert "key: AUDIT_CHAIN_ENABLED\n        value: \"false\"" in render
    assert "key: OTEL_TRACES_ENABLED\n        value: \"false\"" in render
    assert "key: WAF_REQUIRED\n        value: \"false\"" in render
    assert "key: SIEM_REQUIRED\n        value: \"false\"" in render
    assert "key: SOC_PSEUDONYM_KEY\n        sync: false" in render
    assert "key: AUDIT_CHAIN_HMAC_KEY\n        sync: false" in render


def test_security_rules_detect_missing_audit_metrics_not_only_zero_values() -> None:
    rules = _text(REPO_ROOT / "ops/prometheus/security.rules.yml")
    assert "absent(coderoute_audit_chain_valid)" in rules
    assert "absent(coderoute_audit_chain_last_verify_timestamp_seconds)" in rules


def test_chaos_probe_never_stops_or_mutates_dependencies() -> None:
    probe = _text(BACKEND_ROOT / "scripts/chaos_dependency_probe.py")
    forbidden = ("docker stop", "kubectl delete", "systemctl stop", "render services", "terminate")
    assert all(item not in probe.lower() for item in forbidden)
    assert "/health/live" in probe
    assert "/health/readiness" in probe

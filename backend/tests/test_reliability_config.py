import pytest

from app.reliability_config import ReliabilitySettings


def _settings(**overrides) -> ReliabilitySettings:
    values = {
        "metrics_enabled": True,
        "metrics_token": "m" * 40,
        "evidence_enabled": True,
        "evidence_token": "e" * 40,
        "slo_availability_percent": 99.9,
        "slo_p95_latency_ms": 1000,
        "slo_max_5xx_percent": 1.0,
        "dr_rpo_minutes": 5,
        "dr_rto_minutes": 30,
        "backup_required": True,
        "backup_s3_bucket": "coderoute-backups",
        "backup_s3_prefix": "coderoute/production",
        "backup_primary_region": "frankfurt",
        "backup_target_region": "paris",
        "backup_require_off_region": True,
        "backup_encryption_key_id": "backup-key-2026-08",
    }
    values.update(overrides)
    return ReliabilitySettings(**values)


def test_hardened_production_reliability_config_is_accepted() -> None:
    settings = _settings()
    settings.validate(production=True)
    safe = settings.safe_policy()
    assert safe["slo"]["availability_percent"] == 99.9
    assert safe["dr"]["off_region_required"] is True
    assert safe["dr"]["encryption_key_id"] == "backup-key-2026-08"
    rendered = str(safe)
    assert "metrics_token" not in rendered
    assert "evidence_token" not in rendered
    assert "AWS_SECRET_ACCESS_KEY" not in rendered
    assert "BACKUP_ENCRYPTION_KEY_B64" not in rendered


def test_short_machine_tokens_are_rejected_in_production() -> None:
    with pytest.raises(RuntimeError, match="METRICS_TOKEN"):
        _settings(metrics_token="short").validate(production=True)
    with pytest.raises(RuntimeError, match="RELIABILITY_EVIDENCE_TOKEN"):
        _settings(evidence_token="short").validate(production=True)


def test_backup_same_region_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="différente"):
        _settings(backup_target_region="FRANKFURT").validate(production=True)


def test_backup_required_needs_bucket_region_and_key_id() -> None:
    with pytest.raises(RuntimeError) as exc:
        _settings(
            backup_s3_bucket="",
            backup_target_region="",
            backup_encryption_key_id="",
        ).validate(production=True)
    message = str(exc.value)
    assert "BACKUP_S3_BUCKET" in message
    assert "BACKUP_TARGET_REGION" in message
    assert "BACKUP_ENCRYPTION_KEY_ID" in message

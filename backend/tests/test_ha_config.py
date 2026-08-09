import pytest

from app.core.config import Settings


def _production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "secret_key": "a-strong-secret-key-for-production-1234567890",
        "csrf_secret": "a-different-csrf-secret-for-production-0987654321",
        "database_url": "postgresql+psycopg://coderoute:secret@db.internal/coderoute",
        "cors_origins": "https://coderoute.gov.gn",
        "allowed_hosts": "api.coderoute.gov.gn",
        "enable_api_docs": False,
        "auto_create_tables": False,
        "redis_url": "redis://coderoute-shared-state:6379",
        "redis_required": True,
        "ha_mode": True,
        "expected_api_instances": 2,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_ha_configuration_is_accepted() -> None:
    settings = _production_settings()
    settings.validate_production_secrets()


def test_ha_mode_requires_shared_state() -> None:
    settings = _production_settings(redis_url="")
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        settings.validate_production_secrets()


def test_ha_mode_requires_at_least_two_instances() -> None:
    settings = _production_settings(expected_api_instances=1)
    with pytest.raises(RuntimeError, match="EXPECTED_API_INSTANCES"):
        settings.validate_production_secrets()


def test_invalid_shared_state_scheme_is_rejected() -> None:
    settings = _production_settings(redis_url="http://cache.internal")
    with pytest.raises(RuntimeError, match="redis:// ou rediss://"):
        settings.validate_production_secrets()

import pytest

from app import seed_demo


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    # Ces tests changent ENVIRONMENT : ne pas laisser une configuration
    # « production » en cache pour les tests suivants.
    yield
    seed_demo.get_settings.cache_clear()


def test_demo_seed_allowed_in_development(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    seed_demo.get_settings.cache_clear()

    seed_demo.ensure_demo_seed_allowed()


def test_demo_seed_blocked_outside_development(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv(seed_demo.ALLOW_NON_DEV_SEED_ENV, raising=False)
    seed_demo.get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="blocked outside development"):
        seed_demo.ensure_demo_seed_allowed()


def test_demo_seed_can_be_explicitly_allowed_for_disposable_non_dev(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv(seed_demo.ALLOW_NON_DEV_SEED_ENV, "true")
    seed_demo.get_settings.cache_clear()

    seed_demo.ensure_demo_seed_allowed()


def test_demo_seed_override_is_ignored_in_production(monkeypatch) -> None:
    # Régression : la dérogation ne doit jamais créer de comptes à mot de passe
    # connu sur une base de production.
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv(seed_demo.ALLOW_NON_DEV_SEED_ENV, "true")
    seed_demo.get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="always in production"):
        seed_demo.ensure_demo_seed_allowed()


@pytest.mark.parametrize("environment", ["production", "Production"])
def test_full_seed_override_is_ignored_in_production(monkeypatch, environment) -> None:
    from unittest.mock import MagicMock, patch

    from app.seed_full import _guard

    monkeypatch.setenv("ALLOW_DEMO_SEED_NON_DEV", "true")
    with patch("app.core.config.get_settings", return_value=MagicMock(environment=environment)):
        with pytest.raises(RuntimeError, match="Seed bloqué en production"):
            _guard()


def test_full_seed_override_still_allowed_on_disposable_staging(monkeypatch) -> None:
    from unittest.mock import MagicMock, patch

    from app.seed_full import _guard

    monkeypatch.setenv("ALLOW_DEMO_SEED_NON_DEV", "true")
    with patch("app.core.config.get_settings", return_value=MagicMock(environment="staging")):
        _guard()

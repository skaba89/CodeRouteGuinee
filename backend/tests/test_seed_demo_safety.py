import pytest

from app import seed_demo


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

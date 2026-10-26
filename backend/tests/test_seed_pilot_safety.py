"""SEC-01 : le seed pilote ne doit jamais toucher une base de production."""
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import seed_pilote_conakry as pilot


@pytest.mark.parametrize("environment", ["production", "Production", " PRODUCTION "])
@pytest.mark.parametrize("override", [None, "true", "false"])
def test_pilot_seed_blocks_production_before_database_or_questions(monkeypatch, environment, override):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("PILOT_CENTER_PASSWORD", "test-only-custom-password")
    if override is None:
        monkeypatch.delenv("ALLOW_DEMO_SEED_NON_DEV", raising=False)
    else:
        monkeypatch.setenv("ALLOW_DEMO_SEED_NON_DEV", override)
    # Reproduit le cas d'un cache construit dans un environnement moins strict.
    monkeypatch.setattr(pilot, "get_settings", lambda: SimpleNamespace(environment="development"))
    database = Mock(side_effect=AssertionError("Aucune session DB ne doit être ouverte"))
    questions = Mock(side_effect=AssertionError("Aucune question ne doit être insérée"))
    monkeypatch.setattr(pilot, "SessionLocal", database)
    monkeypatch.setattr(pilot, "seed_questions", questions)

    with pytest.raises(RuntimeError, match="Seed pilote bloqué en production"):
        pilot.run()

    database.assert_not_called()
    questions.assert_not_called()


def test_pilot_seed_blocks_production_from_settings_without_environment_override(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("ALLOW_DEMO_SEED_NON_DEV", "true")
    monkeypatch.setattr(pilot, "get_settings", lambda: SimpleNamespace(environment="production"))
    database = Mock(side_effect=AssertionError("Pas de DB"))
    monkeypatch.setattr(pilot, "SessionLocal", database)
    with pytest.raises(RuntimeError, match="Seed pilote bloqué en production"):
        pilot.run()
    database.assert_not_called()


def test_module_entrypoint_refuses_production_with_override():
    backend = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "app.seed_pilote_conakry"],
        cwd=backend,
        env={
            "PYTHONPATH": str(backend),
            "ENVIRONMENT": "production",
            "DATABASE_URL": "sqlite+pysqlite:///:memory:",
            "AUTO_CREATE_TABLES": "false",
            "ALLOW_DEMO_SEED_NON_DEV": "true",
            "SENTRY_DSN": "",
            "OTEL_SDK_DISABLED": "true",
        },
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode != 0
    assert "Seed pilote bloqué en production" in result.stderr


@pytest.mark.parametrize("environment", ["test", "staging", "unknown", ""])
def test_pilot_seed_requires_explicit_authorization_outside_development(monkeypatch, environment):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.delenv("ALLOW_DEMO_SEED_NON_DEV", raising=False)
    database = Mock(side_effect=AssertionError("Pas de DB"))
    monkeypatch.setattr(pilot, "SessionLocal", database)
    with pytest.raises(RuntimeError, match="base jetable hors production"):
        pilot.run()
    database.assert_not_called()


@pytest.mark.parametrize("environment,override", [
    ("development", None), (" Development ", None), ("staging", "true"), ("test", "true"),
])
def test_pilot_seed_preserves_allowed_disposable_environments(monkeypatch, environment, override):
    monkeypatch.setenv("ENVIRONMENT", environment)
    if override is None:
        monkeypatch.delenv("ALLOW_DEMO_SEED_NON_DEV", raising=False)
    else:
        monkeypatch.setenv("ALLOW_DEMO_SEED_NON_DEV", override)

    class DatabaseReached(Exception):
        """Sentinelle : aucune connexion réelle n'est créée par le test."""

    database = Mock(side_effect=DatabaseReached)
    monkeypatch.setattr(pilot, "SessionLocal", database)
    with pytest.raises(DatabaseReached):
        pilot.run()
    database.assert_called_once_with()

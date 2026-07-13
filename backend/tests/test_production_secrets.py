"""
Test — validation renforcée des secrets de production.

Un secret peut ne pas être un « placeholder » tout en étant trivialement
faible. Un audit de sécurité externe (exigé pour un déploiement national)
le relèverait. L'application refuse donc de démarrer en production avec une
configuration dangereuse.
"""
from __future__ import annotations

import secrets

import pytest

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    base = dict(
        environment="production",
        secret_key=secrets.token_hex(32),
        csrf_secret=secrets.token_hex(32),
        database_url="postgresql://user:pass@host:5432/db",
        enable_api_docs=False,
        cors_origins="https://coderoute.gov.gn",
        allowed_hosts="coderoute.gov.gn",
    )
    base.update(overrides)
    return Settings(**base)


def test_configuration_valide_demarre() -> None:
    _settings().validate_production_secrets()  # ne doit pas lever


def test_refuse_secret_trop_court() -> None:
    with pytest.raises(RuntimeError, match="trop court"):
        _settings(secret_key="abc123").validate_production_secrets()


def test_refuse_secret_faible_connu() -> None:
    with pytest.raises(RuntimeError):
        _settings(secret_key="password").validate_production_secrets()


def test_refuse_secrets_identiques() -> None:
    """Réutiliser le même secret pour deux usages cryptographiques est une faute."""
    same = secrets.token_hex(32)
    with pytest.raises(RuntimeError, match="différents"):
        _settings(secret_key=same, csrf_secret=same).validate_production_secrets()


def test_refuse_secret_peu_varie() -> None:
    with pytest.raises(RuntimeError):
        _settings(secret_key="a" * 40).validate_production_secrets()


def test_refuse_sqlite_en_production() -> None:
    with pytest.raises(RuntimeError, match="SQLite"):
        _settings(database_url="sqlite:///./prod.db").validate_production_secrets()


def test_refuse_docs_api_exposees() -> None:
    with pytest.raises(RuntimeError, match="ENABLE_API_DOCS"):
        _settings(enable_api_docs=True).validate_production_secrets()


def test_refuse_cors_localhost() -> None:
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        _settings(cors_origins="http://localhost:5173").validate_production_secrets()


def test_developpement_non_impacte() -> None:
    """En développement, la validation ne s'applique pas (secrets faibles tolérés)."""
    s = Settings(
        environment="development",
        secret_key="dev", csrf_secret="dev",
        database_url="sqlite:///./dev.db",
    )
    s.validate_production_secrets()  # ne doit pas lever

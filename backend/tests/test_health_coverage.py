"""
Tests health.py — couverture /health et /health/readiness.

Cible : app/routers/health.py (21% → 95%+)
Lignes non couvertes : 23-65 (_build_configuration_check), 83-119 (readiness)
"""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.routers.health import _build_configuration_check

# ── /health ──────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        with TestClient(app) as client:
            r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "service" in data

    def test_health_no_auth_required(self):
        with TestClient(app) as client:
            r = client.get("/health")
        assert r.status_code == 200

    def test_health_readiness_returns_dict(self):
        with TestClient(app) as client:
            r = client.get("/health/readiness")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert "checks" in data
        assert data["status"] in ("ready", "degraded")

    def test_readiness_contains_all_check_keys(self):
        with TestClient(app) as client:
            r = client.get("/health/readiness")
        checks = r.json()["checks"]
        assert "database" in checks
        assert "schema" in checks
        assert "migrations" in checks
        assert "configuration" in checks

    def test_readiness_database_ok(self):
        with TestClient(app) as client:
            r = client.get("/health/readiness")
        assert r.json()["checks"]["database"]["status"] == "ok"

    def test_readiness_schema_has_tables(self):
        with TestClient(app) as client:
            r = client.get("/health/readiness")
        schema = r.json()["checks"]["schema"]
        assert "critical_tables" in schema
        assert len(schema["critical_tables"]) > 0

    def test_readiness_migrations_version_present(self):
        with TestClient(app) as client:
            r = client.get("/health/readiness")
        migrations = r.json()["checks"]["migrations"]
        assert "version" in migrations

    def test_readiness_schema_no_missing_tables(self):
        with TestClient(app) as client:
            r = client.get("/health/readiness")
        schema = r.json()["checks"]["schema"]
        assert schema.get("missing_tables", []) == []


# ── _build_configuration_check ────────────────────────────────────

class TestBuildConfigurationCheck:
    """Tests unitaires de la fonction de validation de configuration."""

    def _make_settings(self, **overrides):
        """Crée un mock de settings avec des valeurs valides par défaut."""
        s = MagicMock()
        s.environment = overrides.get("environment", "development")
        s.secret_key = overrides.get("secret_key", "a" * 64)
        s.database_url = overrides.get("database_url", "postgresql://localhost/test")
        s.auto_create_tables = overrides.get("auto_create_tables", False)
        s.cors_origin_list = overrides.get("cors_origins", ["http://localhost:5173"])
        s.allowed_host_list = overrides.get("allowed_hosts", ["localhost"])
        s.enable_api_docs = overrides.get("enable_api_docs", True)
        s.admin_registration_token = overrides.get("admin_registration_token", "token123")
        s.bootstrap_admin_email = overrides.get("bootstrap_admin_email", "admin@test.com")
        return s

    def test_valid_dev_config_returns_ok(self):
        result = _build_configuration_check(self._make_settings())
        assert result["status"] == "ok"
        assert result["errors"] == []

    def test_default_secret_key_is_error(self):
        s = self._make_settings(secret_key="change-me-in-production")
        result = _build_configuration_check(s)
        assert result["status"] == "error"
        assert any("SECRET_KEY" in e for e in result["errors"])

    def test_short_secret_key_is_warning_in_dev(self):
        s = self._make_settings(secret_key="short")
        result = _build_configuration_check(s)
        assert "SECRET_KEY" in " ".join(result["warnings"])
        assert result["status"] in ("warning", "ok")

    def test_sqlite_in_dev_is_warning(self):
        s = self._make_settings(database_url="sqlite:///./test.db")
        result = _build_configuration_check(s)
        assert any("PostgreSQL" in w for w in result["warnings"])

    def test_sqlite_in_production_is_error(self):
        s = self._make_settings(environment="production", database_url="sqlite:///./test.db",
                                secret_key="a" * 64, cors_origins=["https://coderoute.gov.gn"],
                                allowed_hosts=["coderoute.gov.gn"], enable_api_docs=False)
        result = _build_configuration_check(s)
        assert result["status"] == "error"
        assert any("PostgreSQL" in e for e in result["errors"])

    def test_auto_create_tables_in_production_is_error(self):
        s = self._make_settings(
            environment="production",
            auto_create_tables=True,
            cors_origins=["https://coderoute.gov.gn"],
            allowed_hosts=["coderoute.gov.gn"],
            enable_api_docs=False,
            secret_key="a" * 64,
        )
        result = _build_configuration_check(s)
        assert any("AUTO_CREATE_TABLES" in e for e in result["errors"])

    def test_empty_cors_origins_is_error(self):
        s = self._make_settings(cors_origins=[])
        result = _build_configuration_check(s)
        assert result["status"] == "error"
        assert any("CORS_ORIGINS" in e for e in result["errors"])

    def test_wildcard_cors_is_error(self):
        s = self._make_settings(cors_origins=["*"])
        result = _build_configuration_check(s)
        assert any("wildcard" in e for e in result["errors"])

    def test_localhost_cors_in_production_is_error(self):
        s = self._make_settings(
            environment="production",
            cors_origins=["http://localhost:3000"],
            allowed_hosts=["coderoute.gov.gn"],
            enable_api_docs=False,
            secret_key="a" * 64,
        )
        result = _build_configuration_check(s)
        assert any("localhost" in e or "local" in e.lower() for e in result["errors"])

    def test_empty_allowed_hosts_is_error(self):
        s = self._make_settings(allowed_hosts=[])
        result = _build_configuration_check(s)
        assert any("ALLOWED_HOSTS" in e for e in result["errors"])

    def test_wildcard_allowed_hosts_is_error_in_production(self):
        s = self._make_settings(
            environment="production",
            allowed_hosts=["*"],
            cors_origins=["https://coderoute.gov.gn"],
            enable_api_docs=False,
            secret_key="a" * 64,
        )
        result = _build_configuration_check(s)
        assert any("wildcard" in e.lower() or "ALLOWED_HOSTS" in e for e in result["errors"])

    def test_api_docs_in_production_is_error(self):
        s = self._make_settings(
            environment="production",
            enable_api_docs=True,
            cors_origins=["https://coderoute.gov.gn"],
            allowed_hosts=["coderoute.gov.gn"],
            secret_key="a" * 64,
        )
        result = _build_configuration_check(s)
        assert any("ENABLE_API_DOCS" in e for e in result["errors"])

    def test_missing_admin_token_in_production_is_error(self):
        s = self._make_settings(
            environment="production",
            admin_registration_token="",
            cors_origins=["https://coderoute.gov.gn"],
            allowed_hosts=["coderoute.gov.gn"],
            enable_api_docs=False,
            secret_key="a" * 64,
        )
        result = _build_configuration_check(s)
        assert any("ADMIN_REGISTRATION_TOKEN" in e for e in result["errors"])

    def test_missing_bootstrap_email_in_production_is_warning(self):
        s = self._make_settings(
            environment="production",
            bootstrap_admin_email="",
            cors_origins=["https://coderoute.gov.gn"],
            allowed_hosts=["coderoute.gov.gn"],
            enable_api_docs=False,
            secret_key="a" * 64,
            admin_registration_token="tok",
        )
        result = _build_configuration_check(s)
        assert any("BOOTSTRAP_ADMIN_EMAIL" in w for w in result["warnings"])

    def test_result_contains_metadata_fields(self):
        s = self._make_settings()
        result = _build_configuration_check(s)
        assert "environment" in result
        assert "cors_origins_count" in result
        assert "allowed_hosts_count" in result
        assert "api_docs_enabled" in result

    def test_status_warning_when_only_warnings(self):
        s = self._make_settings(secret_key="short")
        result = _build_configuration_check(s)
        if not result["errors"]:
            assert result["status"] == "warning"

    def test_status_error_overrides_warning(self):
        s = self._make_settings(secret_key="change-me-in-production", cors_origins=[])
        result = _build_configuration_check(s)
        assert result["status"] == "error"
        assert len(result["errors"]) >= 2


# ── Readiness avec DB erreur simulée ─────────────────────────────

class TestReadinessDegraded:
    def test_readiness_degraded_when_db_fails(self):
        """Simule une panne DB — le readiness doit retourner degraded."""
        from sqlalchemy.exc import OperationalError

        from app.db.session import get_db

        def bad_db():
            mock = MagicMock()
            mock.execute.side_effect = OperationalError("Connection refused", None, None)
            yield mock

        with TestClient(app) as client:
            app.dependency_overrides[get_db] = bad_db
            try:
                r = client.get("/health/readiness")
                data = r.json()
                assert data["checks"]["database"]["status"] == "error"
                assert data["status"] == "degraded"
            finally:
                app.dependency_overrides.pop(get_db, None)

from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.main import app
from app.routers.health import _build_configuration_check


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_reports_database_schema_and_migrations() -> None:
    client = TestClient(app)
    response = client.get("/health/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "degraded"}
    assert body["checks"]["configuration"]["status"] in {"ok", "warning", "error"}
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["schema"]["status"] == "ok"
    assert "users" in body["checks"]["schema"]["critical_tables"]
    assert body["checks"]["migrations"]["status"] in {"ok", "warning"}


def test_production_configuration_check_rejects_unsafe_defaults() -> None:
    settings = SimpleNamespace(
        environment="production",
        secret_key="change-me-in-production",
        database_url="sqlite:///./coderoute.db",
        auto_create_tables=True,
        cors_origin_list=["http://localhost:5173", "*"],
        allowed_host_list=["localhost", "*"],
        enable_api_docs=True,
        admin_registration_token=None,
        bootstrap_admin_email=None,
    )

    check = _build_configuration_check(settings)

    assert check["status"] == "error"
    assert "SECRET_KEY must be replaced" in check["errors"]
    assert "DATABASE_URL should use PostgreSQL outside local development" in check["errors"]
    assert "AUTO_CREATE_TABLES must be false outside local development" in check["errors"]
    assert "CORS_ORIGINS must not contain wildcard origin" in check["errors"]
    assert "ALLOWED_HOSTS must not contain wildcard host in production" in check["errors"]
    assert "ALLOWED_HOSTS must not contain local hosts in production" in check["errors"]
    assert "ENABLE_API_DOCS must be false in production" in check["errors"]
    assert "ADMIN_REGISTRATION_TOKEN is required in production" in check["errors"]


def test_production_configuration_check_accepts_hardened_settings() -> None:
    settings = SimpleNamespace(
        environment="production",
        secret_key="prod-secret-key-with-more-than-32-characters",
        database_url="postgresql+psycopg://coderoute:secret@postgres:5432/coderoute",
        auto_create_tables=False,
        cors_origin_list=["https://coderoute.gov.gn", "https://admin.coderoute.gov.gn"],
        allowed_host_list=["api.coderoute.gov.gn"],
        enable_api_docs=False,
        admin_registration_token="private-admin-bootstrap-token",
        bootstrap_admin_email="admin@coderoute.gov.gn",
    )

    check = _build_configuration_check(settings)

    assert check["status"] == "ok"
    assert check["errors"] == []

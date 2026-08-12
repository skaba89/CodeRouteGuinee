from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.routers import health as health_router
from app.routers.health import _build_configuration_check


def test_health_liveness_does_not_depend_on_external_services() -> None:
    with TestClient(app) as client:
        for path in ("/health", "/health/live"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
            assert "runtime" in response.json()


def test_readiness_reports_database_schema_migrations_and_shared_state() -> None:
    # Le context manager exécute le lifespan FastAPI et donc init_db(). Sans lui,
    # un SQLite :memory: neuf ne contient logiquement aucune table et readiness
    # doit répondre 503. Le test doit valider l'application démarrée, pas un
    # objet ASGI avant son startup.
    with TestClient(app) as client:
        response = client.get("/health/readiness")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["blocking_checks"] == []
        assert body["checks"]["configuration"]["status"] in {"ok", "warning"}
        assert body["checks"]["database"]["status"] == "ok"
        assert body["checks"]["schema"]["status"] == "ok"
        assert "users" in body["checks"]["schema"]["critical_tables"]
        assert body["checks"]["migrations"]["status"] in {"ok", "warning"}
        assert body["checks"]["shared_state"]["status"] in {"ok", "disabled", "degraded"}


def test_readiness_stays_200_when_reconstructible_shared_state_is_degraded(monkeypatch) -> None:
    monkeypatch.setattr(
        health_router,
        "check_shared_state",
        lambda: {
            "status": "degraded",
            "required": False,
            "backend": "redis-compatible",
            "detail": "ConnectionError",
        },
    )
    with TestClient(app) as client:
        response = client.get("/health/readiness")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert "shared_state" not in body["blocking_checks"]
        assert body["checks"]["shared_state"]["status"] == "degraded"


def test_readiness_returns_503_when_required_shared_state_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        health_router,
        "check_shared_state",
        lambda: {
            "status": "error",
            "required": True,
            "backend": "redis-compatible",
            "detail": "ConnectionError",
        },
    )
    with TestClient(app) as client:
        response = client.get("/health/readiness")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert "shared_state" in body["blocking_checks"]


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
        redis_url="",
        redis_required=True,
        ha_mode=True,
        expected_api_instances=1,
    )

    check = _build_configuration_check(settings)

    assert check["status"] == "error"
    assert any("SECRET_KEY must be replaced" in error for error in check["errors"])
    assert "DATABASE_URL should use PostgreSQL outside local development" in check["errors"]
    assert "AUTO_CREATE_TABLES must be false outside local development" in check["errors"]
    assert "CORS_ORIGINS must not contain wildcard origin" in check["errors"]
    assert "ALLOWED_HOSTS must not contain wildcard host in production" in check["errors"]
    assert "ALLOWED_HOSTS must not contain local hosts in production" in check["errors"]
    assert "ENABLE_API_DOCS must be false in production" in check["errors"]
    assert "ADMIN_REGISTRATION_TOKEN is required in production" in check["errors"]
    assert "REDIS_URL is required when HA_MODE or REDIS_REQUIRED is enabled" in check["errors"]
    assert "EXPECTED_API_INSTANCES must be >= 2 when HA_MODE is enabled" in check["errors"]


def test_production_configuration_check_accepts_hardened_ha_settings() -> None:
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
        redis_url="redis://coderoute-keyvalue:6379",
        redis_required=False,
        ha_mode=True,
        expected_api_instances=2,
    )

    check = _build_configuration_check(settings)

    assert check["status"] == "ok"
    assert check["errors"] == []
    assert check["ha_mode"] is True
    assert check["expected_api_instances"] == 2

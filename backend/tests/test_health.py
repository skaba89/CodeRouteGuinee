from fastapi.testclient import TestClient

from app.main import app


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
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["schema"]["status"] == "ok"
    assert "users" in body["checks"]["schema"]["critical_tables"]
    assert body["checks"]["migrations"]["status"] in {"ok", "warning"}

from fastapi.testclient import TestClient

from app.main import app


def test_supervision_logs_requires_admin_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/supervision/audit-logs")

    assert response.status_code == 401

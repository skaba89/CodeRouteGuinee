from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_export_csv_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/export.csv")

    assert response.status_code == 401

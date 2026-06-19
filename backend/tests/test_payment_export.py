from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers


def test_admin_payment_export_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/payments/admin/export.csv")
    assert response.status_code == 401


def test_admin_payment_export_accessible_with_auth() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        response = client.get("/api/v1/payments/admin/export.csv", headers=headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

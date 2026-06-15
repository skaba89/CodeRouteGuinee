from fastapi.testclient import TestClient

from app.main import app


def test_admin_payment_export_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/payments/admin/export.csv")

    assert response.status_code == 401

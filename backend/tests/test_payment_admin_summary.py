from fastapi.testclient import TestClient

from app.main import app


def test_admin_payment_summary_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/payments/admin/summary")

    assert response.status_code == 401

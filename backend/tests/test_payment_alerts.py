from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers


def test_payment_alerts_require_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/payments/admin/reconciliation/alerts")
    assert response.status_code == 401


def test_payment_alerts_accessible_with_auth() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        response = client.get("/api/v1/payments/admin/reconciliation/alerts", headers=headers)
    assert response.status_code == 200


def test_filtered_payment_alerts_require_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/payments/admin/reconciliation/alerts?provider=orange_money&limit=25")
    assert response.status_code == 401

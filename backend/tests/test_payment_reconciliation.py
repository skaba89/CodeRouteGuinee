from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers


def test_payment_reconciliation_items_require_authentication() -> None:
    with TestClient(app) as client:
        _ = get_admin_headers(client)
        response = client.get("/api/v1/payments/admin/reconciliation/items")

    assert response.status_code == 401


def test_filtered_payment_reconciliation_items_require_authentication() -> None:
    with TestClient(app) as client:
        _ = get_admin_headers(client)
        response = client.get("/api/v1/payments/admin/reconciliation/items?provider=orange_money&status=paid")

    assert response.status_code == 401

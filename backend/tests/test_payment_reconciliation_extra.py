from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers


def test_payment_reconciliation_items_limit_requires_authentication() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        response = client.get("/api/v1/payments/admin/reconciliation/items?limit=5")

    assert response.status_code == 401

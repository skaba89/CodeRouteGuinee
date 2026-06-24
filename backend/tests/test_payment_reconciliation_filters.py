from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers


def test_payment_reconciliation_items_date_filters_require_authentication() -> None:
    with TestClient(app) as client:
        get_admin_headers(client)
        response = client.get("/api/v1/payments/admin/reconciliation/items?date_from=2026-01-01T00:00:00&date_to=2026-12-31T23:59:59")

    assert response.status_code == 401

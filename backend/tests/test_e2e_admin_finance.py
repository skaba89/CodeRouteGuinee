from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_payment import Payment
from app.routers import auth as _auth_module
from tests.conftest import TEST_BOOTSTRAP_TOKEN, get_admin_headers, get_center_headers


def _admin_headers(client: TestClient) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"admin-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    _auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    register_response = client.post(
        "/api/v1/auth/register",
        headers={"X-Admin-Registration-Token": TEST_BOOTSTRAP_TOKEN},
        json={
            "email": email,
            "full_name": "Admin E2E Finance",
            "password": password,
            "role": "admin",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_payments(provider: str) -> None:
    init_db()
    db = SessionLocal()
    try:
        db.add_all(
            [
                Payment(
                    reference=f"PAY-E2E-{uuid4().hex[:10]}",
                    booking_reference="BOOK-E2E-DUPLICATE",
                    amount_gnf=250000,
                    provider=provider,
                    phone="+224622000001",
                    status="paid",
                    receipt_number=f"REC-E2E-{uuid4().hex[:10]}",
                ),
                Payment(
                    reference=f"PAY-E2E-{uuid4().hex[:10]}",
                    booking_reference="BOOK-E2E-DUPLICATE",
                    amount_gnf=250000,
                    provider=provider,
                    phone="+224622000002",
                    status="failed",
                    receipt_number=f"REC-E2E-{uuid4().hex[:10]}",
                ),
                Payment(
                    reference=f"PAY-E2E-{uuid4().hex[:10]}",
                    booking_reference="BOOK-E2E-UNUSUAL",
                    amount_gnf=1500000,
                    provider=provider,
                    phone="+224622000003",
                    status="paid",
                    receipt_number=f"REC-E2E-{uuid4().hex[:10]}",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


def test_admin_finance_reconciliation_end_to_end() -> None:
    provider = f"e2e_provider_{uuid4().hex[:8]}"

    with TestClient(app) as client:
        _ = get_admin_headers(client)
        _ = get_center_headers(client)
        headers = _admin_headers(client)
        _seed_payments(provider)

        summary_response = client.get(
            f"/api/v1/payments/admin/summary?provider={provider}",
            headers=headers,
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["total_count"] == 3
        assert summary["total_amount_gnf"] == 2000000
        assert summary["by_status"]["paid"]["count"] == 2
        assert summary["by_status"]["failed"]["count"] == 1

        items_response = client.get(
            f"/api/v1/payments/admin/reconciliation/items?provider={provider}&limit=10",
            headers=headers,
        )
        assert items_response.status_code == 200
        assert len(items_response.json()) == 3

        alerts_response = client.get(
            f"/api/v1/payments/admin/reconciliation/alerts?provider={provider}&limit=10",
            headers=headers,
        )
        assert alerts_response.status_code == 200
        alert_types = {alert["type"] for alert in alerts_response.json()}
        assert "status" in alert_types
        assert "amount" in alert_types
        assert "duplicate_booking" in alert_types

        export_response = client.get(
            f"/api/v1/payments/admin/export.csv?provider={provider}",
            headers=headers,
        )
        assert export_response.status_code == 200
        assert "reference;booking_reference;amount_gnf;provider;status;receipt_number;created_at" in export_response.text
        assert provider in export_response.text

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=payments.export_csv&limit=25",
            headers=headers,
        )
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()
        assert any(log["action"] == "payments.export_csv" for log in audit_logs)

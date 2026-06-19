from sqlalchemy import select
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from tests.conftest import get_admin_headers
from app.models_audit import AuditLog


def test_payment_failed_audit_log_is_written_for_unknown_booking() -> None:
    missing_booking_reference = "GN-BOOK-MISSING-AUDIT"

    with TestClient(app) as client:
        headers = get_admin_headers(client)
        response = client.post(
            "/api/v1/payments",
            headers=headers,
            json={
                "booking_reference": missing_booking_reference,
                "amount_gnf": 250000,
                "provider": "orange_money",
                "phone": "+224622000000",
            },
        )

    assert response.status_code == 404

    with SessionLocal() as db:
        audit_log = db.scalar(
            select(AuditLog)
            .where(AuditLog.action == "payment.failed")
            .where(AuditLog.entity_id == missing_booking_reference)
        )
        assert audit_log is not None
        assert audit_log.details["reason"] == "booking_not_found"
        assert audit_log.details["amount_gnf"] == 250000

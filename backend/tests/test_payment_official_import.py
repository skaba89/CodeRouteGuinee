from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_payment import Payment
from app.models_session import ExamSession
from app.routers import auth as _auth_module
from tests.conftest import TEST_BOOTSTRAP_TOKEN


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-payment-import-{suffix}@coderoute.gn"
    password = "StrongPass123!"
    _auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    response = client.post(
        "/api/v1/auth/register",
        headers={"X-Admin-Registration-Token": TEST_BOOTSTRAP_TOKEN},
            json={"email": email, "full_name": "Admin Import Paiement", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def _seed_booking() -> str:
    init_db()
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        candidate = Candidate(
            reference=f"GN-CAND-PAY-{suffix}",
            first_name="Fatoumata",
            last_name="Camara",
            identity_number=f"GN-PAY-ID-{suffix}",
            phone="+224620000010",
            permit_category="B",
        )
        center = Center(
            code=f"PAY-CTR-{suffix}",
            name="Centre Paiement",
            city="Conakry",
            address="Kaloum",
            capacity=20,
            max_sessions_per_week=3,
            status="accredited",
        )
        db.add(candidate)
        db.add(center)
        db.commit()
        db.refresh(candidate)
        db.refresh(center)
        session = ExamSession(
            reference=f"GN-PAY-SESSION-{suffix}",
            center_id=center.id,
            starts_at=datetime.now(UTC) + timedelta(days=5),
            capacity=20,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        booking = Booking(
            reference=f"GN-PAY-BOOK-{suffix}",
            candidate_id=candidate.id,
            session_id=session.id,
            verification_code=f"PAY-VERIFY-{suffix}",
        )
        db.add(booking)
        db.commit()
        return booking.reference


def test_official_payment_import_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/payments/admin/import-official",
            json={
                "source": "Orange Money",
                "reason": "Rapprochement quotidien",
                "payments": [
                    {
                        "booking_reference": "GN-PAY-BOOK-001",
                        "amount_gnf": 250000,
                        "provider": "orange_money",
                        "phone": "+224620000010",
                        "status": "paid",
                        "receipt_number": "OM-001",
                    }
                ],
            },
        )

    assert response.status_code == 401


def test_admin_can_import_official_payments_with_audit_log() -> None:
    booking_reference = _seed_booking()
    receipt_number = f"OM-{uuid4().hex[:8].upper()}"

    with TestClient(app) as client:
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/payments/admin/import-official",
            headers=headers,
            json={
                "source": "Orange Money",
                "reason": "Rapprochement quotidien",
                "payments": [
                    {
                        "booking_reference": booking_reference,
                        "amount_gnf": 250000,
                        "provider": "orange_money",
                        "phone": "+224620000010",
                        "status": "paid",
                        "receipt_number": receipt_number,
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["imported"] == 1
        assert payload["created"] == 1
        assert payload["updated"] == 0
        reference = payload["references"][0]

        update_response = client.post(
            "/api/v1/payments/admin/import-official",
            headers=headers,
            json={
                "source": "Orange Money",
                "reason": "Correction statut operateur",
                "payments": [
                    {
                        "booking_reference": booking_reference,
                        "amount_gnf": 250000,
                        "provider": "orange_money",
                        "phone": "+224620000010",
                        "status": "pending",
                        "receipt_number": receipt_number.lower(),
                    }
                ],
            },
        )

        assert update_response.status_code == 200
        assert update_response.json()["updated"] == 1
        assert update_response.json()["references"] == [reference]

        payment_response = client.get(f"/api/v1/payments/{reference}", headers=headers)
        assert payment_response.status_code == 200
        assert payment_response.json()["status"] == "pending"
        assert payment_response.json()["receipt_number"] == receipt_number

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.action == "payments.official_import")
                .where(AuditLog.entity == "payment")
                .order_by(AuditLog.created_at.desc())
            )
            assert audit_log is not None
            assert audit_log.details["source"] == "Orange Money"
            assert audit_log.details["imported"] == 1


def test_official_payment_import_dry_run_does_not_write() -> None:
    booking_reference = _seed_booking()
    receipt_number = f"OM-DRY-{uuid4().hex[:8].upper()}"

    with TestClient(app) as client:
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/payments/admin/import-official",
            headers=headers,
            json={
                "source": "Orange Money",
                "reason": "Simulation rapprochement",
                "dry_run": True,
                "payments": [
                    {
                        "booking_reference": booking_reference,
                        "amount_gnf": 250000,
                        "provider": "orange_money",
                        "phone": "+224620000010",
                        "status": "paid",
                        "receipt_number": receipt_number,
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["dry_run"] is True
        assert payload["created"] == 1
        assert payload["updated"] == 0

        with SessionLocal() as db:
            payment = db.scalar(select(Payment).where(Payment.receipt_number == receipt_number))
            assert payment is None


def test_official_payment_import_rejects_duplicate_receipts_and_unknown_booking() -> None:
    booking_reference = _seed_booking()

    with TestClient(app) as client:
        headers = _admin_headers(client)
        duplicate = client.post(
            "/api/v1/payments/admin/import-official",
            headers=headers,
            json={
                "source": "MTN MoMo",
                "reason": "Doublon volontaire",
                "payments": [
                    {
                        "booking_reference": booking_reference,
                        "amount_gnf": 250000,
                        "provider": "mtn_momo",
                        "phone": "+224620000010",
                        "status": "paid",
                        "receipt_number": "MOMO-DUP",
                    },
                    {
                        "booking_reference": booking_reference,
                        "amount_gnf": 250000,
                        "provider": "mtn_momo",
                        "phone": "+224620000010",
                        "status": "paid",
                        "receipt_number": "momo-dup",
                    },
                ],
            },
        )
        assert duplicate.status_code == 422
        assert "MOMO-DUP" in str(duplicate.json()["detail"])

        unknown = client.post(
            "/api/v1/payments/admin/import-official",
            headers=headers,
            json={
                "source": "MTN MoMo",
                "reason": "Reservation inconnue",
                "payments": [
                    {
                        "booking_reference": "UNKNOWN-BOOKING",
                        "amount_gnf": 250000,
                        "provider": "mtn_momo",
                        "phone": "+224620000010",
                        "status": "paid",
                        "receipt_number": "MOMO-UNKNOWN",
                    }
                ],
            },
        )
        assert unknown.status_code == 422
        assert "UNKNOWN-BOOKING" in str(unknown.json()["detail"])

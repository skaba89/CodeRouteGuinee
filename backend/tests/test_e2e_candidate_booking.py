from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_center import Center
from app.models_session import ExamSession
from tests.conftest import get_admin_headers, get_center_headers


def _seed_center_and_session() -> tuple[str, str, str]:
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    try:
        center = Center(
            code=f"CTR-E2E-{suffix}",
            name="Centre E2E Conakry",
            city="Conakry",
            address="Route Le Prince",
            capacity=20,
            max_sessions_per_week=3,
            status="accredited",
        )
        db.add(center)
        db.commit()
        db.refresh(center)
        session = ExamSession(
            reference=f"GN-SESSION-E2E-{suffix}",
            center_id=center.id,
            starts_at=datetime.now(UTC) + timedelta(days=7),
            capacity=20,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return center.id, center.code, session.id
    finally:
        db.close()


def test_candidate_booking_payment_convocation_and_entry_flow() -> None:
    center_id, center_code, session_id = _seed_center_and_session()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)

        candidate_response = client.post(
            "/api/v1/candidates",
            json={
                "first_name": "Mamadou",
                "last_name": f"E2E-{suffix}",
                "identity_number": f"GN-E2E-{suffix}",
                "phone": "+224622123456",
                "permit_category": "B",
            },
            headers=admin_headers,
        )
        assert candidate_response.status_code == 201
        candidate = candidate_response.json()

        booking_response = client.post(
            "/api/v1/bookings",
            json={"candidate_id": candidate["id"], "session_id": session_id},
            headers=admin_headers,
        )
        assert booking_response.status_code == 201
        booking = booking_response.json()

        payment_response = client.post(
            "/api/v1/payments",
            json={
                "booking_reference": booking["reference"],
                "amount_gnf": 250000,
                "provider": "orange_money",
                "phone": "+224622123456",
            },
            headers=admin_headers,
        )
        assert payment_response.status_code == 201
        payment = payment_response.json()
        assert payment["booking_reference"] == booking["reference"]
        assert payment["status"] == "paid"

        convocation_response = client.get(
            f"/api/v1/bookings/{booking['reference']}/convocation",
            headers=admin_headers,
        )
        assert convocation_response.status_code == 200
        convocation = convocation_response.json()
        assert convocation["booking_reference"] == booking["reference"]
        assert convocation["center"]["code"] == center_code

        pdf_response = client.get(
            f"/api/v1/documents/convocations/{booking['reference']}.pdf",
            headers=admin_headers,
        )
        assert pdf_response.status_code == 200
        assert pdf_response.content.startswith(b"%PDF")
        assert pdf_response.headers["content-type"] == "application/pdf"
        assert f"coderoute-convocation-{booking['reference']}.pdf" in pdf_response.headers["content-disposition"]
        assert b"Document administratif - Convocation candidat" in pdf_response.content

        entry_response = client.post(
            "/api/v1/entries/validate",
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": center_code,
            },
            headers=center_headers,
        )
        assert entry_response.status_code == 200
        assert entry_response.json()["allowed"] is True

        duplicate_entry_response = client.post(
            "/api/v1/entries/validate",
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": center_code,
            },
            headers=center_headers,
        )
        assert duplicate_entry_response.status_code == 200
        assert duplicate_entry_response.json()["reason"] == "already_checked_in"

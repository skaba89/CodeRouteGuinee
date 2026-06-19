from datetime import datetime, timedelta
from app.time_utils import utc_now
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_center_incident import CenterIncident
from app.models_device_session import DeviceSession
from app.models_exam_attempt import ExamAttempt
from app.models_exam_monitoring import ExamMonitoringEvent
from app.models_payment import Payment
from app.models_session import ExamSession


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-operations-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Operations", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def _seed_operations_alerts() -> None:
    init_db()
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        candidate = Candidate(
            reference=f"GN-OPS-CAND-{suffix}",
            first_name="Mamadou",
            last_name="Diallo",
            identity_number=f"GN-OPS-ID-{suffix}",
            phone="+224620000020",
            permit_category="B",
        )
        center = Center(
            code=f"OPS-CTR-{suffix}",
            name="Centre Operations",
            city="Conakry",
            address="Kaloum",
            capacity=20,
            status="accredited",
        )
        db.add(candidate)
        db.add(center)
        db.commit()
        db.refresh(candidate)
        db.refresh(center)

        session = ExamSession(
            reference=f"GN-OPS-SESSION-{suffix}",
            center_id=center.id,
            starts_at=utc_now() + timedelta(days=1),
            capacity=20,
        )
        booking = Booking(
            reference=f"GN-OPS-BOOK-{suffix}",
            candidate_id=candidate.id,
            session_id="pending",
            verification_code=f"OPS-VERIFY-{suffix}",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        booking.session_id = session.id
        db.add(booking)
        db.commit()

        attempt = ExamAttempt(candidate_id=candidate.id, session_id=session.id, status="started")
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        db.add(CenterIncident(center_id=center.id, session_id=session.id, attempt_id=attempt.id, severity="critical", description="Incident critique centre"))
        db.add(DeviceSession(center_id=center.id, session_id=session.id, attempt_id=attempt.id, device_key=f"OPS-DEVICE-{suffix}", status="suspicious"))
        db.add(ExamMonitoringEvent(center_id=center.id, session_id=session.id, attempt_id=attempt.id, event_type="screen_switch", severity="high", risk_score=7))
        db.add(
            Payment(
                reference=f"GN-OPS-PAY-{suffix}",
                booking_reference=booking.reference,
                amount_gnf=250000,
                provider="orange_money",
                phone="+224620000020",
                status="pending",
                receipt_number=f"OPS-RECEIPT-{suffix}",
            )
        )
        db.commit()


def test_operations_summary_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/operations/summary")

    assert response.status_code == 401


def test_operations_summary_reports_critical_signals_and_audit_log() -> None:
    _seed_operations_alerts()

    with TestClient(app) as client:
        headers = _admin_headers(client)
        response = client.get("/api/v1/operations/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"warning", "critical"}
    assert payload["open_incidents"] >= 1
    assert payload["critical_incidents"] >= 1
    assert payload["high_risk_exam_events"] >= 1
    assert payload["suspicious_devices"] >= 1
    assert payload["payment_alerts"] >= 1
    assert any(alert["code"] == "critical_incidents" for alert in payload["alerts"])

    with SessionLocal() as db:
        audit_log = db.scalar(
            select(AuditLog)
            .where(AuditLog.action == "operations.summary_viewed")
            .where(AuditLog.entity == "operations")
            .order_by(AuditLog.created_at.desc())
        )
        assert audit_log is not None
        assert audit_log.details["status"] in {"warning", "critical"}

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.db.session import SessionLocal, engine, init_db
from app.main import app
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_payment import Payment
from app.models_payment_refund import PaymentRefundRequest
from app.models_session import ExamSession
from app.models_user import User
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _user(db, role: str, marker: str) -> User:
    user = User(
        email=f"refund-{role}-{marker}@coderoute.test",
        full_name=f"Refund {role}",
        password_hash=get_password_hash("RefundWorkflow123!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _paid_fixture(db, marker: str, *, booking_status: str = "paid", payment_status: str = "paid"):
    candidate_user = _user(db, "candidate", f"candidate-{marker}")
    candidate = Candidate(
        reference=f"GN-CODE-REFUND-{marker}",
        first_name="Saran",
        last_name="Conde",
        identity_number=f"ID-REFUND-{marker}",
        phone="+224622000099",
        email=candidate_user.email,
        permit_category="B",
        status="verified",
        user_id=candidate_user.id,
    )
    db.add(candidate)
    center = Center(
        code=f"REF-{marker}",
        name=f"Centre Refund {marker}",
        city="Conakry",
        commune="Kaloum",
        prefecture="Conakry",
        address="Kaloum",
        capacity=35,
        max_sessions_per_week=3,
        status="accredited",
    )
    db.add(center)
    db.flush()
    session = ExamSession(
        reference=f"GN-SESSION-REFUND-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7),
        capacity=35,
        status="open",
    )
    db.add(session)
    db.flush()
    booking = Booking(
        reference=f"GN-CONV-REFUND-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        status=booking_status,
        verification_code=f"VERIFY-REFUND-{marker}",
    )
    db.add(booking)
    payment = Payment(
        reference=f"GN-PAY-REFUND-{marker}",
        booking_reference=booking.reference,
        amount_gnf=150_000,
        provider="orange_money",
        phone=candidate.phone,
        status=payment_status,
        receipt_number=f"GN-RECEIPT-REFUND-{marker}",
        external_reference=f"PROVIDER-PAY-{marker}",
        paid_at=datetime.now(UTC).replace(tzinfo=None) if payment_status == "paid" else None,
    )
    db.add(payment)
    db.flush()
    booking.payment_reference = payment.reference
    db.add(booking)
    return candidate_user, candidate, booking, payment


def test_refund_table_and_safe_legacy_route_replacement_exist_after_alembic_head() -> None:
    init_db()
    tables = set(inspect(engine).get_table_names())
    assert "payment_refund_requests" in tables

    routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/payments/{reference}/refund"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]
    assert len(routes) == 1
    assert routes[0].endpoint.__name__ == "request_refund"


def test_request_and_approval_do_not_mark_money_refunded_before_external_evidence() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    candidate_user, _candidate, booking, payment = _paid_fixture(db, marker)
    admin = _user(db, "super_admin", f"admin-{marker}")
    candidate_headers = _headers(candidate_user)
    admin_headers = _headers(admin)
    refs = {"payment": payment.reference, "booking": booking.reference}
    db.commit()
    db.close()

    with TestClient(app) as client:
        requested = client.post(
            f"/api/v1/payments/{refs['payment']}/refund",
            headers=candidate_headers,
            json={"reason": "Je demande le remboursement de ce paiement avant la session."},
        )
        assert requested.status_code == 202
        refund_id = requested.json()["id"]
        assert requested.json()["status"] == "requested"

        retry = client.post(
            f"/api/v1/payments/{refs['payment']}/refund",
            headers=candidate_headers,
            json={"reason": "Je demande le remboursement de ce paiement avant la session."},
        )
        assert retry.status_code == 200
        assert retry.json()["id"] == refund_id

        visible = client.get(f"/api/v1/payments/refunds/{refund_id}", headers=candidate_headers)
        assert visible.status_code == 200
        assert visible.json()["status"] == "requested"

        approved = client.post(
            f"/api/v1/payments/refunds/{refund_id}/decision",
            headers=admin_headers,
            json={"decision": "approved", "reason": "Demande recevable, remboursement opérateur à exécuter."},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

    db = SessionLocal()
    stored_payment = db.scalar(select(Payment).where(Payment.reference == refs["payment"]))
    stored_booking = db.scalar(select(Booking).where(Booking.reference == refs["booking"]))
    assert stored_payment is not None and stored_payment.status == "paid"
    assert stored_booking is not None and stored_booking.status == "paid"
    db.close()

    with TestClient(app) as client:
        completed = client.post(
            f"/api/v1/payments/refunds/{refund_id}/complete",
            headers=admin_headers,
            json={
                "provider_refund_reference": "RF-12345",
                "evidence_reference": "GED-REFUND-12345",
                "notes": "Remboursement confirmé dans le portail opérateur.",
            },
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"
        assert completed.json()["provider_refund_reference"] == "RF-12345"
        assert completed.json()["evidence_reference"] == "GED-REFUND-12345"

        replay = client.post(
            f"/api/v1/payments/refunds/{refund_id}/complete",
            headers=admin_headers,
            json={
                "provider_refund_reference": "RF-12345",
                "evidence_reference": "GED-REFUND-12345",
                "notes": "Remboursement confirmé dans le portail opérateur.",
            },
        )
        assert replay.status_code == 200
        assert replay.json()["status"] == "completed"

        conflicting_replay = client.post(
            f"/api/v1/payments/refunds/{refund_id}/complete",
            headers=admin_headers,
            json={
                "provider_refund_reference": "RF-DIFFERENT",
                "evidence_reference": "GED-DIFFERENT",
                "notes": "Référence contradictoire qui doit être refusée.",
            },
        )
        assert conflicting_replay.status_code == 409
        assert conflicting_replay.json()["detail"]["code"] == "REFUND_COMPLETION_ALREADY_RECORDED"

    db = SessionLocal()
    stored_payment = db.scalar(select(Payment).where(Payment.reference == refs["payment"]))
    stored_booking = db.scalar(select(Booking).where(Booking.reference == refs["booking"]))
    refund = db.get(PaymentRefundRequest, refund_id)
    assert stored_payment is not None and stored_payment.status == "refunded"
    assert stored_booking is not None and stored_booking.status == "cancelled"
    assert stored_booking.cancelled_at is not None
    assert refund is not None and refund.status == "completed"
    completed_audit = db.scalar(
        select(AuditLog)
        .where(AuditLog.action == "payment.refund_completed", AuditLog.entity_id == refund_id)
        .limit(1)
    )
    assert completed_audit is not None
    assert completed_audit.details["completion_mode"] == "operator_attested_external_evidence"
    assert completed_audit.details["exam_attempt_exists"] is False
    db.close()


def test_rejected_refund_leaves_payment_and_booking_untouched() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    candidate_user, _candidate, booking, payment = _paid_fixture(db, f"reject-{marker}")
    admin = _user(db, "super_admin", f"reject-admin-{marker}")
    candidate_headers = _headers(candidate_user)
    admin_headers = _headers(admin)
    payment_ref = payment.reference
    booking_ref = booking.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        requested = client.post(
            f"/api/v1/payments/{payment_ref}/refund",
            headers=candidate_headers,
            json={"reason": "Je demande un remboursement qui sera finalement refusé."},
        )
        assert requested.status_code == 202
        refund_id = requested.json()["id"]

        rejected = client.post(
            f"/api/v1/payments/refunds/{refund_id}/decision",
            headers=admin_headers,
            json={"decision": "rejected", "reason": "La demande ne respecte pas la procédure de remboursement."},
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "rejected"

        completion = client.post(
            f"/api/v1/payments/refunds/{refund_id}/complete",
            headers=admin_headers,
            json={
                "provider_refund_reference": "RF-NOT-ALLOWED",
                "evidence_reference": "GED-NOT-ALLOWED",
                "notes": "Cette finalisation doit être bloquée après rejet.",
            },
        )
        assert completion.status_code == 409
        assert completion.json()["detail"]["code"] == "REFUND_APPROVAL_REQUIRED"

        second_request = client.post(
            f"/api/v1/payments/{payment_ref}/refund",
            headers=candidate_headers,
            json={"reason": "Deuxième demande après décision finale sans réouverture admin."},
        )
        assert second_request.status_code == 409
        assert second_request.json()["detail"]["code"] == "REFUND_REQUEST_ALREADY_DECIDED"

    db = SessionLocal()
    assert db.scalar(select(Payment).where(Payment.reference == payment_ref)).status == "paid"
    assert db.scalar(select(Booking).where(Booking.reference == booking_ref)).status == "paid"
    db.close()


def test_checked_in_refund_without_attempt_cancels_future_exam_eligibility() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    candidate_user, _candidate, booking, payment = _paid_fixture(
        db, f"checked-no-attempt-{marker}", booking_status="checked_in"
    )
    admin = _user(db, "super_admin", f"checked-no-attempt-admin-{marker}")
    candidate_headers = _headers(candidate_user)
    admin_headers = _headers(admin)
    payment_ref = payment.reference
    booking_ref = booking.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        requested = client.post(
            f"/api/v1/payments/{payment_ref}/refund",
            headers=candidate_headers,
            json={"reason": "Remboursement après scan mais avant création de la tentative."},
        )
        refund_id = requested.json()["id"]
        assert client.post(
            f"/api/v1/payments/refunds/{refund_id}/decision",
            headers=admin_headers,
            json={"decision": "approved", "reason": "Remboursement exceptionnel validé avant examen."},
        ).status_code == 200
        assert client.post(
            f"/api/v1/payments/refunds/{refund_id}/complete",
            headers=admin_headers,
            json={
                "provider_refund_reference": "RF-BEFORE-EXAM-123",
                "evidence_reference": "GED-BEFORE-EXAM-123",
                "notes": "Preuve opérateur reçue avant création de la tentative.",
            },
        ).status_code == 200

    db = SessionLocal()
    assert db.scalar(select(Payment).where(Payment.reference == payment_ref)).status == "refunded"
    stored_booking = db.scalar(select(Booking).where(Booking.reference == booking_ref))
    assert stored_booking.status == "cancelled"
    assert stored_booking.cancelled_at is not None
    assert "Remboursement enregistré" in (stored_booking.notes or "")
    db.close()


def test_checked_in_refund_preserves_exam_history_when_attempt_exists() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    candidate_user, candidate, booking, payment = _paid_fixture(
        db, f"checked-attempt-{marker}", booking_status="checked_in"
    )
    db.add(
        ExamAttempt(
            candidate_id=candidate.id,
            session_id=booking.session_id,
            status="submitted",
            score=30,
            passed=False,
            submitted_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    admin = _user(db, "super_admin", f"checked-attempt-admin-{marker}")
    candidate_headers = _headers(candidate_user)
    admin_headers = _headers(admin)
    payment_ref = payment.reference
    booking_ref = booking.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        requested = client.post(
            f"/api/v1/payments/{payment_ref}/refund",
            headers=candidate_headers,
            json={"reason": "Remboursement exceptionnel après une tentative déjà enregistrée."},
        )
        assert requested.status_code == 202
        refund_id = requested.json()["id"]
        assert client.post(
            f"/api/v1/payments/refunds/{refund_id}/decision",
            headers=admin_headers,
            json={"decision": "approved", "reason": "Exception administrative documentée après examen."},
        ).status_code == 200
        completed = client.post(
            f"/api/v1/payments/refunds/{refund_id}/complete",
            headers=admin_headers,
            json={
                "provider_refund_reference": "RF-CHECKED-123",
                "evidence_reference": "GED-CHECKED-123",
                "notes": "Preuve opérateur archivée après passage à l'examen.",
            },
        )
        assert completed.status_code == 200

    db = SessionLocal()
    assert db.scalar(select(Payment).where(Payment.reference == payment_ref)).status == "refunded"
    stored_booking = db.scalar(select(Booking).where(Booking.reference == booking_ref))
    assert stored_booking.status == "checked_in"
    assert "Remboursement enregistré" in (stored_booking.notes or "")
    db.close()


def test_unsettled_or_foreign_payment_cannot_open_refund() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    owner, _candidate, _booking, pending_payment = _paid_fixture(
        db, f"pending-{marker}", payment_status="pending", booking_status="pending_payment"
    )
    attacker = _user(db, "candidate", f"attacker-{marker}")
    _paid_owner, _candidate2, _booking2, paid_payment = _paid_fixture(db, f"foreign-{marker}")
    owner_headers = _headers(owner)
    attacker_headers = _headers(attacker)
    pending_ref = pending_payment.reference
    paid_ref = paid_payment.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        pending = client.post(
            f"/api/v1/payments/{pending_ref}/refund",
            headers=owner_headers,
            json={"reason": "Un paiement pending ne doit pas être remboursé comme s'il était encaissé."},
        )
        assert pending.status_code == 409
        assert pending.json()["detail"]["code"] == "REFUND_PAYMENT_NOT_SETTLED"

        foreign = client.post(
            f"/api/v1/payments/{paid_ref}/refund",
            headers=attacker_headers,
            json={"reason": "Je ne dois pas pouvoir demander le remboursement du paiement d'un autre candidat."},
        )
        assert foreign.status_code == 403

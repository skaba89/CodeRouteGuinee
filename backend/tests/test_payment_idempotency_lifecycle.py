from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select

from app.db.session import SessionLocal, engine, init_db
from app.main import app
from app.mobile_money import ProviderResult
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_payment import Payment
from app.models_session import ExamSession
from app.models_user import User
from app.routers import payments
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _candidate_fixture(db, marker: str, *, booking_status: str = "confirmed", session_status: str = "open"):
    user = User(
        email=f"payment-idem-{marker}@coderoute.test",
        full_name="Payment Idempotency Candidate",
        password_hash=get_password_hash("PaymentIdem123!"),
        role="candidate",
        is_active=True,
    )
    db.add(user)
    db.flush()
    candidate = Candidate(
        reference=f"GN-CODE-PAYIDEM-{marker}",
        first_name="Alpha",
        last_name="Diallo",
        identity_number=f"ID-PAYIDEM-{marker}",
        phone="+224622000099",
        email=user.email,
        permit_category="B",
        status="verified",
        user_id=user.id,
    )
    db.add(candidate)
    center = Center(
        code=f"PAYIDEM-{marker}",
        name=f"Centre Payment {marker}",
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
        reference=f"GN-SESSION-PAYIDEM-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3),
        capacity=35,
        status=session_status,
    )
    db.add(session)
    db.flush()
    booking = Booking(
        reference=f"GN-CONV-PAYIDEM-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        status=booking_status,
        verification_code=f"VERIFY-PAYIDEM-{marker}",
    )
    db.add(booking)
    db.flush()
    return user, candidate, session, booking


def test_checkout_url_column_exists_after_alembic_head() -> None:
    init_db()
    columns = {column["name"] for column in inspect(engine).get_columns("payments")}
    assert "checkout_url" in columns


def test_payment_post_route_is_replaced_once() -> None:
    routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/payments"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]
    assert len(routes) == 1
    assert routes[0].endpoint.__name__ == "create_payment_idempotent"


def test_pending_checkout_retry_returns_same_payment_without_second_provider_call(monkeypatch) -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    user, _candidate, _session, booking = _candidate_fixture(db, marker)
    headers = _headers(user)
    booking_ref = booking.reference
    db.commit()
    db.close()

    calls = {"count": 0}

    def provider(provider: str, phone: str, amount: int) -> ProviderResult:
        calls["count"] += 1
        return ProviderResult(
            provider="wave",
            status="pending",
            external_reference=f"WAVE-IDEM-{marker}",
            message="Paiement Wave initié — en attente de confirmation",
            checkout_url=f"https://pay.wave.test/checkout/{marker}",
        )

    monkeypatch.setattr(payments, "simulate_mobile_money_payment", provider)

    request = {
        "booking_reference": booking_ref,
        "provider": "wave",
        "phone": "+224622000099",
    }
    with TestClient(app) as client:
        first = client.post("/api/v1/payments", headers=headers, json=request)
        assert first.status_code == 201
        first_payload = first.json()
        assert first_payload["status"] == "pending"
        assert first_payload["checkout_url"] == f"https://pay.wave.test/checkout/{marker}"

        retry = client.post("/api/v1/payments", headers=headers, json=request)
        assert retry.status_code == 200
        retry_payload = retry.json()
        assert retry_payload["reference"] == first_payload["reference"]
        assert retry_payload["external_reference"] == first_payload["external_reference"]
        assert retry_payload["checkout_url"] == first_payload["checkout_url"]
        assert "sans nouveau débit" in retry_payload["message"]

        quote = client.get(f"/api/v1/payments/quote/{booking_ref}", headers=headers)
        assert quote.status_code == 200
        assert quote.json()["source"] == "existing_payment"
        assert quote.json()["payment_reference"] == first_payload["reference"]
        assert quote.json()["payment_status"] == "pending"
        assert quote.json()["checkout_url"] == first_payload["checkout_url"]

    assert calls["count"] == 1
    db = SessionLocal()
    rows = list(db.scalars(select(Payment).where(Payment.booking_reference == booking_ref)).all())
    assert len(rows) == 1
    assert rows[0].checkout_url == f"https://pay.wave.test/checkout/{marker}"
    replay_log = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "payment.idempotent_replay",
            AuditLog.entity_id == rows[0].reference,
        )
        .limit(1)
    )
    assert replay_log is not None
    assert replay_log.details["checkout_url_restored"] is True
    db.close()


def test_failed_payment_can_retry_but_terminal_booking_without_open_payment_cannot_debit(monkeypatch) -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    user, _candidate, _session, booking = _candidate_fixture(db, f"retry-{marker}")
    headers = _headers(user)
    booking_ref = booking.reference
    db.commit()
    db.close()

    calls = {"count": 0}

    def provider(provider: str, phone: str, amount: int) -> ProviderResult:
        calls["count"] += 1
        if calls["count"] == 1:
            return ProviderResult(
                provider="orange_money",
                status="failed",
                external_reference=f"FAILED-{marker}",
                message="Provider temporairement indisponible",
            )
        return ProviderResult(
            provider="orange_money",
            status="paid",
            external_reference=f"PAID-{marker}",
            message="Paiement confirmé",
        )

    monkeypatch.setattr(payments, "simulate_mobile_money_payment", provider)
    request = {
        "booking_reference": booking_ref,
        "provider": "orange_money",
        "phone": "+224622000099",
    }

    with TestClient(app) as client:
        failed = client.post("/api/v1/payments", headers=headers, json=request)
        assert failed.status_code == 201
        assert failed.json()["status"] == "failed"

        paid = client.post("/api/v1/payments", headers=headers, json=request)
        assert paid.status_code == 201
        assert paid.json()["status"] == "paid"

        third = client.post("/api/v1/payments", headers=headers, json=request)
        assert third.status_code == 200
        assert third.json()["reference"] == paid.json()["reference"]

    assert calls["count"] == 2
    db = SessionLocal()
    assert db.scalar(select(func.count(Payment.id)).where(Payment.booking_reference == booking_ref)) == 2
    stored_booking = db.scalar(select(Booking).where(Booking.reference == booking_ref))
    assert stored_booking is not None and stored_booking.status == "paid"
    db.close()

    # Data-drift case: a terminal booking without any open payment must never
    # trigger a new provider call.
    db = SessionLocal()
    user2, _candidate2, _session2, booking2 = _candidate_fixture(
        db, f"drift-{marker}", booking_status="checked_in"
    )
    headers2 = _headers(user2)
    ref2 = booking2.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        blocked = client.post(
            "/api/v1/payments",
            headers=headers2,
            json={
                "booking_reference": ref2,
                "provider": "orange_money",
                "phone": "+224622000099",
            },
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "BOOKING_ALREADY_SETTLED"

        quote = client.get(f"/api/v1/payments/quote/{ref2}", headers=headers2)
        assert quote.status_code == 409
        assert quote.json()["detail"]["code"] == "BOOKING_ALREADY_SETTLED"

    assert calls["count"] == 2


def test_cancelled_or_cancelled_session_blocks_before_provider(monkeypatch) -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    user_cancel, _candidate, _session, booking_cancel = _candidate_fixture(
        db, f"cancel-{marker}", booking_status="cancelled"
    )
    user_session, _candidate2, _session2, booking_session = _candidate_fixture(
        db, f"session-{marker}", session_status="cancelled"
    )
    headers_cancel = _headers(user_cancel)
    headers_session = _headers(user_session)
    ref_cancel = booking_cancel.reference
    ref_session = booking_session.reference
    db.commit()
    db.close()

    calls = {"count": 0}

    def provider(*args, **kwargs):
        calls["count"] += 1
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(payments, "simulate_mobile_money_payment", provider)

    with TestClient(app) as client:
        cancelled = client.post(
            "/api/v1/payments",
            headers=headers_cancel,
            json={"booking_reference": ref_cancel, "provider": "orange_money", "phone": "+224622000099"},
        )
        assert cancelled.status_code == 409
        assert cancelled.json()["detail"]["code"] == "BOOKING_CANCELLED_NOT_PAYABLE"

        session_cancelled = client.post(
            "/api/v1/payments",
            headers=headers_session,
            json={"booking_reference": ref_session, "provider": "orange_money", "phone": "+224622000099"},
        )
        assert session_cancelled.status_code == 409
        assert session_cancelled.json()["detail"]["code"] == "PAYMENT_SESSION_NOT_ACTIVE"

    assert calls["count"] == 0

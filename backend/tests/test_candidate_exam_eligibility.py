from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _user(db, role: str, marker: str, *, center_id: str | None = None) -> User:
    user = User(
        email=f"eligibility-{role}-{marker}@coderoute.test",
        full_name=f"Eligibility {role}",
        password_hash=get_password_hash("Eligibility123!"),
        role=role,
        is_active=True,
        center_id=center_id,
    )
    db.add(user)
    db.flush()
    return user


def _center_session(db, marker: str) -> tuple[Center, ExamSession]:
    center = Center(
        code=f"ELIG-{marker}",
        name=f"Centre éligibilité {marker}",
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
        reference=f"GN-SESSION-ELIG-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5),
        capacity=35,
        status="open",
    )
    db.add(session)
    db.flush()
    return center, session


def _candidate(db, marker: str, user: User, *, candidate_status: str) -> Candidate:
    candidate = Candidate(
        reference=f"GN-CODE-ELIG-{marker}",
        first_name="Aminata",
        last_name="Bah",
        identity_number=f"ID-ELIG-{marker}",
        phone="+224622000099",
        email=user.email,
        permit_category="B",
        status=candidate_status,
        user_id=user.id,
    )
    db.add(candidate)
    db.flush()
    return candidate


def test_paid_registered_candidate_is_denied_at_checkin_until_identity_verified() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    center, session = _center_session(db, marker)
    center_user = _user(db, "center", marker, center_id=center.id)
    candidate_user = _user(db, "candidate", marker)
    candidate = _candidate(db, marker, candidate_user, candidate_status="registered")
    booking = Booking(
        reference=f"GN-CONV-ELIG-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        status="paid",
        verification_code=f"VERIFY-ELIG-{marker}",
    )
    db.add(booking)
    ids = {"candidate": candidate.id}
    refs = {
        "booking": booking.reference,
        "verification": booking.verification_code,
        "center_code": center.code,
    }
    headers = _headers(center_user)
    db.commit()
    db.close()

    with TestClient(app) as client:
        denied = client.post(
            "/api/v1/entries/validate",
            headers=headers,
            json={
                "reference": refs["booking"],
                "verification_code": refs["verification"],
                "center_code": refs["center_code"],
            },
        )
        assert denied.status_code == 200
        assert denied.json()["allowed"] is False
        assert denied.json()["reason"] == "identity_verification_required"
        assert denied.json()["details"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

    db = SessionLocal()
    candidate = db.get(Candidate, ids["candidate"])
    assert candidate is not None
    candidate.status = "verified"
    db.add(candidate)
    db.commit()
    db.close()

    with TestClient(app) as client:
        allowed = client.post(
            "/api/v1/entries/validate",
            headers=headers,
            json={
                "reference": refs["booking"],
                "verification_code": refs["verification"],
                "center_code": refs["center_code"],
            },
        )
        assert allowed.status_code == 200
        assert allowed.json()["allowed"] is True


def test_suspended_candidate_cannot_book_or_obtain_payment_quote() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    _center, session = _center_session(db, f"s-{marker}")
    candidate_user = _user(db, "candidate", f"s-{marker}")
    candidate = _candidate(db, f"s-{marker}", candidate_user, candidate_status="suspended")
    legacy_booking = Booking(
        reference=f"GN-CONV-SUSP-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        status="confirmed",
        verification_code=f"VERIFY-SUSP-{marker}",
    )
    db.add(legacy_booking)
    headers = _headers(candidate_user)
    session_id = session.id
    booking_ref = legacy_booking.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        booking = client.post(
            "/api/v1/bookings/self",
            headers=headers,
            json={"session_id": session_id},
        )
        assert booking.status_code == 409
        assert booking.json()["detail"]["code"] == "CANDIDATE_SUSPENDED"
        assert booking.json()["detail"]["action"] == "booking"

        legacy = client.post(
            "/api/v1/registration/book",
            headers=headers,
            json={"session_id": session_id},
        )
        assert legacy.status_code == 409
        assert legacy.json()["detail"]["code"] == "CANDIDATE_SUSPENDED"

        quote = client.get(
            f"/api/v1/payments/quote/{booking_ref}",
            headers=headers,
        )
        assert quote.status_code == 409
        assert quote.json()["detail"]["code"] == "CANDIDATE_SUSPENDED"
        assert quote.json()["detail"]["action"] == "payment"


def test_suspension_after_verification_blocks_paid_checkin() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    center, session = _center_session(db, f"late-{marker}")
    center_user = _user(db, "center", f"late-{marker}", center_id=center.id)
    candidate_user = _user(db, "candidate", f"late-{marker}")
    candidate = _candidate(db, f"late-{marker}", candidate_user, candidate_status="suspended")
    booking = Booking(
        reference=f"GN-CONV-LATE-SUSP-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        status="paid",
        verification_code=f"VERIFY-LATE-SUSP-{marker}",
    )
    db.add(booking)
    headers = _headers(center_user)
    payload = {
        "reference": booking.reference,
        "verification_code": booking.verification_code,
        "center_code": center.code,
    }
    db.commit()
    db.close()

    with TestClient(app) as client:
        denied = client.post("/api/v1/entries/validate", headers=headers, json=payload)
        assert denied.status_code == 200
        assert denied.json()["allowed"] is False
        assert denied.json()["reason"] == "candidate_suspended"
        assert denied.json()["details"]["code"] == "CANDIDATE_SUSPENDED"
        assert denied.json()["details"]["action"] == "official_exam"

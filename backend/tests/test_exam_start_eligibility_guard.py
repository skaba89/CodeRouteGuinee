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


def _user(db, role: str, marker: str) -> User:
    user = User(
        email=f"start-elig-{role}-{marker}@coderoute.test",
        full_name=f"Start eligibility {role}",
        password_hash=get_password_hash("StartEligibility123!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _fixture(db, marker: str, user: User, candidate_status: str) -> tuple[Candidate, ExamSession, Booking]:
    center = Center(
        code=f"START-{marker}",
        name=f"Centre start {marker}",
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
        reference=f"GN-SESSION-START-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=3),
        capacity=35,
        status="open",
    )
    db.add(session)
    db.flush()
    candidate = Candidate(
        reference=f"GN-CODE-START-{marker}",
        first_name="Ibrahima",
        last_name="Sylla",
        identity_number=f"ID-START-{marker}",
        phone="+224622000099",
        email=user.email,
        permit_category="B",
        status=candidate_status,
        user_id=user.id,
    )
    db.add(candidate)
    db.flush()
    booking = Booking(
        reference=f"GN-CONV-START-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        status="checked_in",
        verification_code=f"VERIFY-START-{marker}",
    )
    db.add(booking)
    db.flush()
    return candidate, session, booking


def test_exam_start_routes_are_replaced_once_by_eligibility_guard() -> None:
    routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) in {
            "/api/v1/exams/start",
            "/api/v1/exams/start-from-booking",
        }
        and "POST" in (getattr(route, "methods", set()) or set())
    ]
    assert sorted(route.path for route in routes) == [
        "/api/v1/exams/start",
        "/api/v1/exams/start-from-booking",
    ]


def test_checked_in_candidate_is_revalidated_before_attempt_creation_or_resume() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    suspended_user = _user(db, "candidate", f"s-{marker}")
    registered_user = _user(db, "candidate", f"r-{marker}")
    suspended, _session_s, booking_s = _fixture(db, f"s-{marker}", suspended_user, "suspended")
    registered, _session_r, booking_r = _fixture(db, f"r-{marker}", registered_user, "registered")
    refs = {
        "suspended_booking": booking_s.reference,
        "registered_booking": booking_r.reference,
        "suspended_id": suspended.id,
        "registered_id": registered.id,
    }
    headers_s = _headers(suspended_user)
    headers_r = _headers(registered_user)
    db.commit()
    db.close()

    with TestClient(app) as client:
        suspended_start = client.post(
            "/api/v1/exams/start-from-booking",
            headers=headers_s,
            json={"booking_reference": refs["suspended_booking"], "device_key": "device-safe"},
        )
        assert suspended_start.status_code == 409
        assert suspended_start.json()["detail"]["code"] == "CANDIDATE_SUSPENDED"
        assert suspended_start.json()["detail"]["action"] == "official_exam"

        unverified_start = client.post(
            "/api/v1/exams/start-from-booking",
            headers=headers_r,
            json={"booking_reference": refs["registered_booking"], "device_key": "device-safe"},
        )
        assert unverified_start.status_code == 409
        assert unverified_start.json()["detail"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

    db = SessionLocal()
    from app.models_exam_attempt import ExamAttempt
    assert db.query(ExamAttempt).filter(ExamAttempt.candidate_id.in_([refs["suspended_id"], refs["registered_id"]])).count() == 0
    db.close()


def test_candidate_cannot_learn_other_booking_eligibility_state() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    owner = _user(db, "candidate", f"owner-{marker}")
    attacker = _user(db, "candidate", f"attacker-{marker}")
    _candidate, _session, booking = _fixture(db, f"owner-{marker}", owner, "suspended")
    booking_ref = booking.reference
    attacker_headers = _headers(attacker)
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/exams/start-from-booking",
            headers=attacker_headers,
            json={"booking_reference": booking_ref, "device_key": "device-safe"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Cette réservation ne vous appartient pas."


def test_admin_override_cannot_start_unverified_candidate() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    candidate_user = _user(db, "candidate", f"candidate-{marker}")
    admin = _user(db, "super_admin", f"admin-{marker}")
    candidate, session, _booking = _fixture(db, f"admin-{marker}", candidate_user, "registered")
    candidate_id = candidate.id
    session_id = session.id
    admin_headers = _headers(admin)
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/exams/start",
            headers=admin_headers,
            json={"candidate_id": candidate_id, "session_id": session_id},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

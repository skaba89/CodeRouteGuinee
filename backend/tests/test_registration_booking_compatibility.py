from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _candidate_user(db, marker: str) -> tuple[User, Candidate]:
    user = User(
        email=f"legacy-booking-{marker}@coderoute.test",
        full_name="Legacy booking candidate",
        password_hash=get_password_hash("LegacyTest123!"),
        role="candidate",
        is_active=True,
    )
    db.add(user)
    db.flush()
    candidate = Candidate(
        reference=f"GN-CODE-LEGACY-{marker}",
        first_name="Mariam",
        last_name="Barry",
        identity_number=f"LEGACY-ID-{marker}",
        phone="+224622000099",
        email=user.email,
        permit_category="B",
        user_id=user.id,
        status="registered",
    )
    db.add(candidate)
    db.flush()
    return user, candidate


def _center(db, marker: str, status_name: str) -> Center:
    center = Center(
        code=f"LEGACY-{marker}",
        name=f"Centre Legacy {marker}",
        city="Conakry",
        commune="Kaloum",
        prefecture="Conakry",
        address="Kaloum",
        capacity=35,
        max_sessions_per_week=3,
        status=status_name,
    )
    db.add(center)
    db.flush()
    return center


def _session(db, center: Center, marker: str, offset_days: int) -> ExamSession:
    session = ExamSession(
        reference=f"GN-SESSION-LEGACY-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=offset_days),
        capacity=35,
        status="planned",
    )
    db.add(session)
    db.flush()
    return session


def test_legacy_registration_routes_are_replaced_once() -> None:
    availability = [
        route for route in app.routes
        if getattr(route, "path", None) == "/api/v1/registration/availability"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]
    booking = [
        route for route in app.routes
        if getattr(route, "path", None) == "/api/v1/registration/book"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]
    assert len(availability) == 1
    assert len(booking) == 1
    assert availability[0].endpoint.__module__.endswith("registration_booking_guard")
    assert booking[0].endpoint.__module__.endswith("registration_booking_guard")


def test_legacy_availability_excludes_non_operational_centers_and_booking_reuses_canonical_rules() -> None:
    init_db()
    marker = uuid4().hex[:10]
    db = SessionLocal()
    user, _candidate = _candidate_user(db, marker)
    headers = _headers(user)
    active_center = _center(db, f"ACTIVE-{marker}", "accredited")
    suspended_center = _center(db, f"SUSP-{marker}", "suspended")
    active_session = _session(db, active_center, f"ACTIVE-{marker}", 5)
    suspended_session = _session(db, suspended_center, f"SUSP-{marker}", 6)
    active_id = active_session.id
    suspended_id = suspended_session.id
    active_ref = active_session.reference
    suspended_ref = suspended_session.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        availability = client.get("/api/v1/registration/availability", headers=headers)
        assert availability.status_code == 200
        refs = {item["session_reference"] for item in availability.json()["items"]}
        assert active_ref in refs
        assert suspended_ref not in refs

        rejected = client.post(
            "/api/v1/registration/book",
            headers=headers,
            json={"session_id": suspended_id},
        )
        assert rejected.status_code == 409

        booked = client.post(
            "/api/v1/registration/book",
            headers=headers,
            json={"session_id": active_id},
        )
        assert booked.status_code == 201
        assert booked.json()["status"] == "confirmed"
        assert booked.json()["session_reference"] == active_ref

        duplicate = client.post(
            "/api/v1/registration/book",
            headers=headers,
            json={"session_id": active_id},
        )
        assert duplicate.status_code == 409

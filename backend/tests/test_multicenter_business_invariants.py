from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

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


def _create_user(db, role: str, *, center_id: str | None = None) -> User:
    user = User(
        email=f"{role}-{uuid4().hex}@coderoute.test",
        full_name=f"Test {role}",
        password_hash=get_password_hash("TestPass123!"),
        role=role,
        is_active=True,
        center_id=center_id,
    )
    db.add(user)
    db.flush()
    return user


def _create_center(db, marker: str, *, prefecture: str, commune: str) -> Center:
    center = Center(
        code=f"CTR-{marker}",
        name=f"Centre {marker}",
        city="Conakry",
        commune=commune,
        prefecture=prefecture,
        address="Kaloum",
        capacity=35,
        max_sessions_per_week=3,
        status="accredited",
    )
    db.add(center)
    db.flush()
    return center


def _create_session(db, center: Center, marker: str, starts_at: datetime) -> ExamSession:
    session = ExamSession(
        reference=f"GN-SESSION-{marker}",
        center_id=center.id,
        starts_at=starts_at,
        capacity=35,
        status="planned",
    )
    db.add(session)
    db.flush()
    return session


def _create_candidate(db, marker: str, *, user: User | None = None) -> Candidate:
    candidate = Candidate(
        reference=f"GN-CODE-{marker}",
        first_name="Mamadou",
        last_name="Diallo",
        identity_number=f"ID-{marker}",
        phone=f"+22462{marker[-7:].replace('-', '0')[:7]}",
        email=user.email if user else None,
        permit_category="B",
        user_id=user.id if user else None,
        status="registered",
    )
    db.add(candidate)
    db.flush()
    return candidate


def _create_booking(db, candidate: Candidate, session: ExamSession, marker: str, status_name: str = "confirmed") -> Booking:
    booking = Booking(
        reference=f"GN-CONV-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        status=status_name,
        verification_code=f"VERIFY-{marker}",
    )
    db.add(booking)
    db.flush()
    return booking


def test_center_cannot_read_or_operate_other_center_resources() -> None:
    init_db()
    marker = uuid4().hex[:10]
    db = SessionLocal()
    starts = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=6)
    center_a = _create_center(db, f"A-{marker}", prefecture=f"PREF-{marker}", commune=f"COM-A-{marker}")
    center_b = _create_center(db, f"B-{marker}", prefecture=f"PREF-{marker}", commune=f"COM-B-{marker}")
    user_a = _create_user(db, "center", center_id=center_a.id)
    session_a = _create_session(db, center_a, f"A-{marker}", starts)
    session_b = _create_session(db, center_b, f"B-{marker}", starts + timedelta(hours=3))
    candidate_a = _create_candidate(db, f"A-{marker}")
    candidate_b = _create_candidate(db, f"B-{marker}")
    booking_a = _create_booking(db, candidate_a, session_a, f"A-{marker}")
    booking_b = _create_booking(db, candidate_b, session_b, f"B-{marker}")
    db.commit()
    refs = {
        "user": user_a,
        "session_b": session_b.id,
        "candidate_b": candidate_b.id,
        "booking_a": booking_a.reference,
        "booking_b": booking_b.reference,
    }
    db.expunge_all()
    db.close()

    with TestClient(app) as client:
        headers = _headers(refs["user"])
        listed = client.get("/api/v1/bookings", headers=headers)
        assert listed.status_code == 200
        listed_refs = {item["reference"] for item in listed.json()["items"]}
        assert refs["booking_a"] in listed_refs
        assert refs["booking_b"] not in listed_refs

        assert client.get(f"/api/v1/bookings/{refs['booking_b']}", headers=headers).status_code == 403
        assert client.get(f"/api/v1/candidates/{refs['candidate_b']}", headers=headers).status_code == 403
        assert client.get(f"/api/v1/sessions/{refs['session_b']}", headers=headers).status_code == 403
        assert client.patch(f"/api/v1/sessions/{refs['session_b']}/open", headers=headers).status_code == 403


def test_candidate_can_cancel_unpaid_booking_then_rebook() -> None:
    init_db()
    marker = uuid4().hex[:10]
    db = SessionLocal()
    center = _create_center(db, marker, prefecture=f"PREF-{marker}", commune=f"COM-{marker}")
    candidate_user = _create_user(db, "candidate")
    candidate = _create_candidate(db, marker, user=candidate_user)
    first = _create_session(
        db,
        center,
        f"1-{marker}",
        datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7),
    )
    second = _create_session(
        db,
        center,
        f"2-{marker}",
        datetime.now(UTC).replace(tzinfo=None) + timedelta(days=8),
    )
    booking = _create_booking(db, candidate, first, marker)
    db.commit()
    headers = _headers(candidate_user)
    booking_ref = booking.reference
    second_id = second.id
    db.expunge_all()
    db.close()

    with TestClient(app) as client:
        cancelled = client.post(f"/api/v1/bookings/{booking_ref}/cancel", headers=headers)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        rebooked = client.post("/api/v1/bookings/self", headers=headers, json={"session_id": second_id})
        assert rebooked.status_code == 201
        assert rebooked.json()["status"] == "confirmed"
        assert rebooked.json()["reference"] != booking_ref


def test_session_cancellation_releases_linked_bookings_and_records_cancel_time() -> None:
    init_db()
    marker = uuid4().hex[:10]
    db = SessionLocal()
    center = _create_center(db, marker, prefecture=f"PREF-{marker}", commune=f"COM-{marker}")
    admin = _create_user(db, "super_admin")
    session = _create_session(
        db,
        center,
        marker,
        datetime.now(UTC).replace(tzinfo=None) + timedelta(days=5),
    )
    candidate = _create_candidate(db, marker)
    booking = _create_booking(db, candidate, session, marker)
    db.commit()
    headers = _headers(admin)
    session_id = session.id
    booking_id = booking.id
    db.expunge_all()
    db.close()

    with TestClient(app) as client:
        response = client.patch(f"/api/v1/sessions/{session_id}/cancel", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    db = SessionLocal()
    stored = db.get(Booking, booking_id)
    assert stored is not None
    assert stored.status == "cancelled"
    assert stored.cancelled_at is not None
    db.close()


def test_commune_stats_count_distinct_centers_not_sessions() -> None:
    init_db()
    marker = uuid4().hex[:10]
    prefecture = f"PREF-STATS-{marker}"
    commune = f"COM-STATS-{marker}"
    db = SessionLocal()
    center = _create_center(db, marker, prefecture=prefecture, commune=commune)
    admin = _create_user(db, "super_admin")
    base = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=10)
    _create_session(db, center, f"1-{marker}", base)
    _create_session(db, center, f"2-{marker}", base + timedelta(days=1))
    db.commit()
    headers = _headers(admin)
    db.expunge_all()
    db.close()

    with TestClient(app) as client:
        response = client.get("/api/v1/sessions/stats/by-commune", headers=headers)
        assert response.status_code == 200
        row = next(item for item in response.json() if item["commune"] == commune and item["prefecture"] == prefecture)
        assert row["centers_count"] == 1
        assert row["sessions_count"] == 2

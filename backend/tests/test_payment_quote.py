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


def _user(db, marker: str) -> User:
    user = User(
        email=f"quote-{marker}@coderoute.test",
        full_name=f"Quote {marker}",
        password_hash=get_password_hash("QuoteTest123!"),
        role="candidate",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _booking_for(db, user: User, marker: str, *, status_name: str = "confirmed") -> Booking:
    center = Center(
        code=f"QUOTE-{marker}",
        name=f"Centre Quote {marker}",
        city="Conakry",
        address="Kaloum",
        capacity=35,
        status="accredited",
    )
    db.add(center)
    db.flush()
    session = ExamSession(
        reference=f"GN-SESSION-QUOTE-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=4),
        capacity=35,
        status="planned",
    )
    db.add(session)
    db.flush()
    candidate = Candidate(
        reference=f"GN-CODE-QUOTE-{marker}",
        first_name="Aissatou",
        last_name="Camara",
        identity_number=f"QUOTE-ID-{marker}",
        phone="+224622000099",
        email=user.email,
        permit_category="B",
        attempt_count=0,
        user_id=user.id,
        status="registered",
    )
    db.add(candidate)
    db.flush()
    booking = Booking(
        reference=f"GN-CONV-QUOTE-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        verification_code=f"VERIFY-QUOTE-{marker}",
        status=status_name,
    )
    db.add(booking)
    db.flush()
    return booking


def test_quote_returns_server_tariff_and_blocks_other_candidate() -> None:
    init_db()
    marker = uuid4().hex[:10]
    db = SessionLocal()
    owner = _user(db, f"owner-{marker}")
    other = _user(db, f"other-{marker}")
    owner_headers = _headers(owner)
    other_headers = _headers(other)
    booking = _booking_for(db, owner, marker)
    reference = booking.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        quote = client.get(f"/api/v1/payments/quote/{reference}", headers=owner_headers)
        assert quote.status_code == 200
        payload = quote.json()
        assert payload["booking_reference"] == reference
        assert payload["amount_gnf"] == 150_000
        assert payload["currency"] == "GNF"
        assert payload["permit_category"] == "B"
        assert payload["attempt_number"] == 1
        assert payload["source"] == "server_tariff"

        forbidden = client.get(f"/api/v1/payments/quote/{reference}", headers=other_headers)
        assert forbidden.status_code == 403


def test_cancelled_booking_has_no_payable_quote() -> None:
    init_db()
    marker = uuid4().hex[:10]
    db = SessionLocal()
    owner = _user(db, f"cancel-{marker}")
    headers = _headers(owner)
    booking = _booking_for(db, owner, marker, status_name="cancelled")
    reference = booking.reference
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.get(f"/api/v1/payments/quote/{reference}", headers=headers)
        assert response.status_code == 409

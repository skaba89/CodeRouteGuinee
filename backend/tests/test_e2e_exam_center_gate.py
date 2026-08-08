from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_question import Question
from app.question_bank_gn import QUESTIONS_GN


def _admin_headers(client: TestClient) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"admin-center-gate-{suffix}@coderoute.local"
    password = "AdminPass123!"
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Admin Center Gate E2E",
            "password": password,
            "role": "admin",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _ensure_official_bank() -> None:
    """Ajoute une banque officielle complète sans dépendre d'un seed global."""
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        for index, row in enumerate(QUESTIONS_GN):
            question = Question(
                category=row["category"],
                text=f"{row['text']} [center-gate-{suffix}-{index}]",
                options=row["options"],
                correct_answer=row["correct_answer"],
                explanation=row.get("explanation", ""),
                is_active=True,
                validation_status="approved",
            )
            db.add(question)
        db.commit()


def _create_center(client: TestClient, headers: dict[str, str], suffix: str) -> dict:
    response = client.post(
        "/api/v1/centers",
        headers=headers,
        json={
            "code": f"GATE-{suffix}",
            "name": f"Centre Gate {suffix}",
            "city": "Conakry",
            "address": "Kaloum",
            "capacity": 35,
            "status": "accredited",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_candidate_booking(
    client: TestClient,
    headers: dict[str, str],
    center: dict,
    suffix: str,
    starts_at: datetime,
) -> tuple[dict, dict, dict]:
    session_response = client.post(
        "/api/v1/sessions",
        headers=headers,
        json={
            "center_id": center["id"],
            "starts_at": starts_at.isoformat(),
            "capacity": 35,
        },
    )
    assert session_response.status_code == 201
    session = session_response.json()

    candidate_response = client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "first_name": "Mamadou",
            "last_name": "Gate",
            "identity_number": f"GN-GATE-{suffix}",
            "phone": "+224620123456",
            "permit_category": "B",
        },
    )
    assert candidate_response.status_code == 201
    candidate = candidate_response.json()

    booking_response = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={"candidate_id": candidate["id"], "session_id": session["id"]},
    )
    assert booking_response.status_code == 201
    return session, candidate, booking_response.json()


def _pay_booking(client: TestClient, headers: dict[str, str], booking: dict) -> None:
    payment = client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "booking_reference": booking["reference"],
            "amount_gnf": 250000,
            "provider": "sandbox",
            "phone": "+224620123456",
        },
    )
    assert payment.status_code == 201
    assert payment.json()["status"] == "paid"


def test_paid_checked_in_candidate_requires_registered_station_to_start_exam() -> None:
    suffix = uuid4().hex[:8].upper()
    with TestClient(app) as client:
        headers = _admin_headers(client)
        _ensure_official_bank()
        center = _create_center(client, headers, suffix)
        session, _candidate, booking = _create_candidate_booking(
            client,
            headers,
            center,
            suffix,
            datetime.now(UTC) + timedelta(minutes=5),
        )

        # Paiement absent : le QR est authentique mais l'entrée reste refusée.
        unpaid_entry = client.post(
            "/api/v1/entries/validate",
            headers=headers,
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": center["code"],
            },
        )
        assert unpaid_entry.status_code == 200
        assert unpaid_entry.json()["allowed"] is False
        assert unpaid_entry.json()["reason"] == "payment_required_before_checkin"

        _pay_booking(client, headers, booking)

        wrong_center = client.post(
            "/api/v1/entries/validate",
            headers=headers,
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": "AUTRE-CENTRE",
            },
        )
        assert wrong_center.status_code == 200
        assert wrong_center.json()["allowed"] is False
        assert wrong_center.json()["reason"] == "wrong_exam_center"

        checked_in = client.post(
            "/api/v1/entries/validate",
            headers=headers,
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": center["code"],
            },
        )
        assert checked_in.status_code == 200
        assert checked_in.json()["allowed"] is True
        assert checked_in.json()["status"] == "checked_in"

        station_key = f"CRG-STATION-{suffix}"
        station = client.post(
            "/api/v1/center-stations",
            headers=headers,
            json={
                "center_id": center["id"],
                "device_key": station_key,
                "label": "Poste sécurisé 01",
                "room": "Salle A",
                "status": "active",
            },
        )
        assert station.status_code == 201

        missing_station = client.post(
            "/api/v1/exams/start-from-booking",
            headers=headers,
            json={"booking_reference": booking["reference"]},
        )
        assert missing_station.status_code == 409
        assert missing_station.json()["detail"]["code"] == "EXAM_STATION_REQUIRED"

        unknown_station = client.post(
            "/api/v1/exams/start-from-booking",
            headers=headers,
            json={
                "booking_reference": booking["reference"],
                "device_key": "CRG-STATION-NON-ENREGISTRE",
            },
        )
        assert unknown_station.status_code == 403
        assert unknown_station.json()["detail"]["code"] == "UNREGISTERED_EXAM_STATION"

        started = client.post(
            "/api/v1/exams/start-from-booking",
            headers=headers,
            json={
                "booking_reference": booking["reference"],
                "device_key": station_key,
                "device_label": "Poste sécurisé 01",
            },
        )
        assert started.status_code == 201
        attempt = started.json()
        assert attempt["session_id"] == session["id"]
        assert attempt["status"] == "started"


def test_checkin_is_rejected_when_session_is_too_far_in_future() -> None:
    suffix = uuid4().hex[:8].upper()
    with TestClient(app) as client:
        headers = _admin_headers(client)
        center = _create_center(client, headers, suffix)
        _session, _candidate, booking = _create_candidate_booking(
            client,
            headers,
            center,
            suffix,
            datetime.now(UTC) + timedelta(days=2),
        )
        _pay_booking(client, headers, booking)

        response = client.post(
            "/api/v1/entries/validate",
            headers=headers,
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": center["code"],
            },
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is False
        assert response.json()["reason"] == "checkin_outside_session_window"
        assert response.json()["details"]["opens_at"]

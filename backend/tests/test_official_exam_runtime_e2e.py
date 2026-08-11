from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.exam_engine import CATEGORY_DISTRIBUTION
from app.main import app
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_center_station import CenterStation
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_payment import Payment
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _user(db, role: str, marker: str, *, center_id: str | None = None) -> User:
    user = User(
        email=f"official-{role}-{marker}@coderoute.test",
        full_name=f"Official {role}",
        password_hash=get_password_hash("OfficialExam123!"),
        role=role,
        is_active=True,
        center_id=center_id,
    )
    db.add(user)
    db.flush()
    return user


def _seed_official_question_bank(db, marker: str) -> dict[str, str]:
    answer_key: dict[str, str] = {}
    number = 0
    for category, count in CATEGORY_DISTRIBUTION.items():
        for index in range(count):
            number += 1
            correct = "Réponse correcte"
            question = Question(
                category=category,
                text=f"Question officielle E2E {marker} {category} {index + 1}",
                options=[correct, "Distracteur A", "Distracteur B", "Distracteur C"],
                correct_answer=correct,
                explanation=f"Explication officielle E2E {number}",
                media_type="image",
                media_url=f"https://media.invalid/{marker}/{number}.webp",
                media_alt=f"Situation routière E2E {number}",
                validation_status="approved",
                is_active=True,
                validated_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(question)
            db.flush()
            answer_key[question.id] = correct
    return answer_key


def test_official_exam_requires_checkin_registered_station_trace_and_server_scoring() -> None:
    init_db()
    marker = uuid4().hex[:10]
    now = datetime.now(UTC).replace(tzinfo=None)
    db = SessionLocal()

    center = Center(
        code=f"OFF-{marker}",
        name=f"Centre officiel {marker}",
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

    center_user = _user(db, "center", marker, center_id=center.id)
    candidate_user = _user(db, "candidate", marker)
    candidate = Candidate(
        reference=f"GN-CODE-OFFICIAL-{marker}",
        first_name="Fatoumata",
        last_name="Camara",
        identity_number=f"OFFICIAL-ID-{marker}",
        phone="+224622000099",
        email=candidate_user.email,
        permit_category="B",
        user_id=candidate_user.id,
        status="verified",
        attempt_count=0,
    )
    db.add(candidate)
    db.flush()

    session = ExamSession(
        reference=f"GN-SESSION-OFFICIAL-{marker}",
        center_id=center.id,
        starts_at=now + timedelta(minutes=2),
        capacity=35,
        status="open",
    )
    db.add(session)
    db.flush()

    device_key = f"station-official-{marker}"
    station = CenterStation(
        center_id=center.id,
        device_key=device_key,
        label="Poste officiel E2E",
        status="active",
        room="Salle A",
        created_by_id=center_user.id,
    )
    db.add(station)
    db.flush()

    booking = Booking(
        reference=f"GN-CONV-OFFICIAL-{marker}",
        candidate_id=candidate.id,
        session_id=session.id,
        status="paid",
        verification_code=f"VERIFY-OFFICIAL-{marker}",
    )
    db.add(booking)
    db.flush()

    payment = Payment(
        reference=f"GN-PAY-OFFICIAL-{marker}",
        booking_reference=booking.reference,
        amount_gnf=150_000,
        provider="sandbox",
        phone=candidate.phone,
        status="paid",
        receipt_number=f"GN-RECEIPT-OFFICIAL-{marker}",
        external_reference=f"SANDBOX-OFFICIAL-{marker}",
        paid_at=now,
    )
    db.add(payment)
    booking.payment_reference = payment.reference
    db.add(booking)

    answer_key = _seed_official_question_bank(db, marker)
    db.commit()

    center_headers = _headers(center_user)
    candidate_headers = _headers(candidate_user)
    booking_ref = booking.reference
    verification_code = booking.verification_code
    center_code = center.code
    db.close()

    with TestClient(app) as client:
        # Une réservation payée ne suffit pas : le contrôle physique est requis.
        before_checkin = client.post(
            "/api/v1/exams/start-from-booking",
            headers=candidate_headers,
            json={"booking_reference": booking_ref, "device_key": device_key},
        )
        assert before_checkin.status_code == 409
        assert before_checkin.json()["detail"]["code"] == "CHECKIN_REQUIRED_BEFORE_EXAM"

        entry = client.post(
            "/api/v1/entries/validate",
            headers=center_headers,
            json={
                "reference": booking_ref,
                "verification_code": verification_code,
                "center_code": center_code,
            },
        )
        assert entry.status_code == 200
        assert entry.json()["allowed"] is True

        # Dès qu'un registre de postes existe, le device devient obligatoire.
        no_station = client.post(
            "/api/v1/exams/start-from-booking",
            headers=candidate_headers,
            json={"booking_reference": booking_ref},
        )
        assert no_station.status_code == 409
        assert no_station.json()["detail"]["code"] == "EXAM_STATION_REQUIRED"

        wrong_station = client.post(
            "/api/v1/exams/start-from-booking",
            headers=candidate_headers,
            json={"booking_reference": booking_ref, "device_key": f"unknown-{marker}"},
        )
        assert wrong_station.status_code == 403
        assert wrong_station.json()["detail"]["code"] == "UNREGISTERED_EXAM_STATION"

        started = client.post(
            "/api/v1/exams/start-from-booking",
            headers=candidate_headers,
            json={
                "booking_reference": booking_ref,
                "device_key": device_key,
                "device_label": "Poste officiel E2E",
            },
        )
        assert started.status_code == 201
        attempt_id = started.json()["id"]
        assert started.json()["status"] == "started"

        # Un retry réseau reprend la même tentative au lieu d'en créer une seconde.
        resumed = client.post(
            "/api/v1/exams/start-from-booking",
            headers=candidate_headers,
            json={"booking_reference": booking_ref, "device_key": device_key},
        )
        assert resumed.status_code == 201
        assert resumed.json()["id"] == attempt_id

        questions = client.get(
            f"/api/v1/exams/{attempt_id}/questions",
            headers=candidate_headers,
        )
        assert questions.status_code == 200
        payload = questions.json()
        assert payload["attempt_id"] == attempt_id
        assert len(payload["questions"]) == 40
        assert payload["duration_seconds"] == 30 * 60
        assert payload["threshold"] == 35
        for item in payload["questions"]:
            assert "correct_answer" not in item
            assert "explanation" not in item
            assert item["media_source"] == "legacy"
            assert item["media_url"].startswith("https://media.invalid/")

        status_response = client.get(
            f"/api/v1/exams/{attempt_id}/status",
            headers=candidate_headers,
        )
        assert status_response.status_code == 200
        assert status_response.json()["question_count"] == 40
        assert status_response.json()["status"] == "started"

        # La notation se fait uniquement avec la clé serveur de la trace.
        submitted = client.post(
            f"/api/v1/exams/{attempt_id}/submit",
            headers=candidate_headers,
            json={"answers": {**answer_key, "not-in-official-trace": "Réponse correcte"}},
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "submitted"
        assert submitted.json()["score"] == 40
        assert submitted.json()["passed"] is True

        results = client.get(
            f"/api/v1/exams/{attempt_id}/results",
            headers=candidate_headers,
        )
        assert results.status_code == 200
        result_payload = results.json()
        assert result_payload["score"] == 40
        assert result_payload["total"] == 40
        assert result_payload["passed"] is True
        assert len(result_payload["questions"]) == 40
        assert all(item["is_correct"] for item in result_payload["questions"])

        certificate = client.get(f"/api/v1/exams/{attempt_id}/certificate/verify")
        assert certificate.status_code == 200
        assert certificate.json()["valid"] is True
        assert certificate.json()["passed"] is True

        # La réservation ne peut pas être réutilisée après une tentative soumise.
        replay = client.post(
            "/api/v1/exams/start-from-booking",
            headers=candidate_headers,
            json={"booking_reference": booking_ref, "device_key": device_key},
        )
        assert replay.status_code == 409
        assert replay.json()["detail"]["code"] == "BOOKING_ALREADY_USED_FOR_EXAM"

        closed_questions = client.get(
            f"/api/v1/exams/{attempt_id}/questions",
            headers=candidate_headers,
        )
        assert closed_questions.status_code == 409

    db = SessionLocal()
    stored_attempt = db.get(ExamAttempt, attempt_id)
    trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt_id))
    stored_candidate = db.scalar(select(Candidate).where(Candidate.reference == f"GN-CODE-OFFICIAL-{marker}"))
    attempts = list(
        db.scalars(
            select(ExamAttempt).where(
                ExamAttempt.candidate_id == stored_candidate.id,
                ExamAttempt.session_id == stored_attempt.session_id,
            )
        ).all()
    )
    assert stored_attempt is not None
    assert stored_attempt.answers is not None
    assert "not-in-official-trace" not in stored_attempt.answers
    assert trace is not None
    assert trace.question_count == 40
    assert len(trace.question_ids) == 40
    assert len(attempts) == 1
    assert stored_candidate.attempt_count == 1
    db.close()
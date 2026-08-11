from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.db.session import SessionLocal, engine, init_db
from app.main import app
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_session import ExamSession
from app.models_user import User
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _user(db, role: str, marker: str) -> User:
    user = User(
        email=f"appeals-{role}-{marker}@coderoute.test",
        full_name=f"Appeals {role}",
        password_hash=get_password_hash("Appeals123!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _candidate(db, marker: str, user: User) -> Candidate:
    candidate = Candidate(
        reference=f"GN-CODE-APPEAL-{marker}",
        first_name="Nene",
        last_name="Camara",
        identity_number=f"ID-APPEAL-{marker}",
        phone="+224622000099",
        email=user.email,
        permit_category="B",
        status="verified",
        user_id=user.id,
    )
    db.add(candidate)
    db.flush()
    return candidate


def _attempt(db, marker: str, candidate: Candidate) -> ExamAttempt:
    center = Center(
        code=f"APP-{marker}",
        name=f"Centre Appeals {marker}",
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
        reference=f"GN-SESSION-APPEAL-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1),
        capacity=35,
        status="completed",
    )
    db.add(session)
    db.flush()
    attempt = ExamAttempt(
        candidate_id=candidate.id,
        session_id=session.id,
        status="submitted",
        score=34,
        passed=False,
        submitted_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(attempt)
    db.flush()
    return attempt


def test_candidate_followup_attempt_column_is_nullable_after_migration() -> None:
    init_db()
    columns = {column["name"]: column for column in inspect(engine).get_columns("candidate_followups")}
    assert columns["attempt_id"]["nullable"] is True


def test_payment_booking_and_other_appeals_work_without_exam_attempt() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    candidate_user = _user(db, "candidate", marker)
    admin = _user(db, "super_admin", marker)
    candidate = _candidate(db, marker, candidate_user)
    candidate_id = candidate.id
    candidate_headers = _headers(candidate_user)
    admin_headers = _headers(admin)
    db.commit()
    db.close()

    with TestClient(app) as client:
        payment = client.post(
            "/api/v1/candidate-submissions",
            headers=candidate_headers,
            json={
                "candidate_id": candidate_id,
                "attempt_id": "",
                "category": "payment",
                "message": "Mon paiement a été débité mais son statut doit être vérifié.",
            },
        )
        assert payment.status_code == 201
        payment_payload = payment.json()
        assert payment_payload["attempt_id"] is None
        assert payment_payload["category"] == "payment"

        booking = client.post(
            "/api/v1/candidate-submissions",
            headers=candidate_headers,
            json={
                "candidate_id": candidate_id,
                "category": "booking",
                "message": "Je souhaite signaler un problème sur ma réservation actuelle.",
            },
        )
        assert booking.status_code == 201
        assert booking.json()["attempt_id"] is None

        other = client.post(
            "/api/v1/candidate-submissions",
            headers=candidate_headers,
            json={
                "candidate_id": candidate_id,
                "attempt_id": None,
                "category": "other",
                "message": "Je souhaite transmettre une demande générale concernant mon dossier.",
            },
        )
        assert other.status_code == 201
        assert other.json()["attempt_id"] is None

        duplicate_payment = client.post(
            "/api/v1/candidate-submissions",
            headers=candidate_headers,
            json={
                "candidate_id": candidate_id,
                "category": "payment",
                "message": "Je tente de dupliquer le même recours de paiement ouvert.",
            },
        )
        assert duplicate_payment.status_code == 409
        assert duplicate_payment.json()["detail"]["code"] == "CANDIDATE_SUBMISSION_ALREADY_OPEN"

        retake = client.post(
            f"/api/v1/candidate-submissions/{payment_payload['id']}/handle",
            headers=admin_headers,
            json={
                "status": "retake_planned",
                "admin_response": "Tentative de rattrapage sur un recours paiement.",
            },
        )
        assert retake.status_code == 409
        assert retake.json()["detail"]["code"] == "RETAKE_REQUIRES_EXAM_ATTEMPT"

        accepted = client.post(
            f"/api/v1/candidate-submissions/{payment_payload['id']}/handle",
            headers=admin_headers,
            json={
                "status": "accepted",
                "admin_response": "Paiement à rapprocher par l'équipe financière.",
            },
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"


def test_exam_result_appeal_still_requires_owned_attempt() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    candidate_user = _user(db, "candidate", f"a-{marker}")
    other_user = _user(db, "candidate", f"b-{marker}")
    candidate = _candidate(db, f"a-{marker}", candidate_user)
    other = _candidate(db, f"b-{marker}", other_user)
    own_attempt = _attempt(db, f"a-{marker}", candidate)
    other_attempt = _attempt(db, f"b-{marker}", other)
    headers = _headers(candidate_user)
    refs = {
        "candidate": candidate.id,
        "own_attempt": own_attempt.id,
        "other_attempt": other_attempt.id,
    }
    db.commit()
    db.close()

    with TestClient(app) as client:
        missing = client.post(
            "/api/v1/candidate-submissions",
            headers=headers,
            json={
                "candidate_id": refs["candidate"],
                "category": "exam_result",
                "message": "Je souhaite contester le résultat mais sans tentative renseignée.",
            },
        )
        assert missing.status_code == 422
        assert missing.json()["detail"]["code"] == "CANDIDATE_SUBMISSION_ATTEMPT_REQUIRED"

        mismatch = client.post(
            "/api/v1/candidate-submissions",
            headers=headers,
            json={
                "candidate_id": refs["candidate"],
                "attempt_id": refs["other_attempt"],
                "category": "exam_result",
                "message": "Je ne dois pas pouvoir rattacher le recours à une autre tentative.",
            },
        )
        assert mismatch.status_code == 409

        valid = client.post(
            "/api/v1/candidate-submissions",
            headers=headers,
            json={
                "candidate_id": refs["candidate"],
                "attempt_id": refs["own_attempt"],
                "category": "exam_result",
                "message": "Je demande une vérification de mon résultat d'examen.",
            },
        )
        assert valid.status_code == 201
        assert valid.json()["attempt_id"] == refs["own_attempt"]

        unsupported = client.post(
            "/api/v1/candidate-submissions",
            headers=headers,
            json={
                "candidate_id": refs["candidate"],
                "category": "made_up_category",
                "message": "Cette catégorie arbitraire doit être refusée proprement.",
            },
        )
        assert unsupported.status_code == 422
        assert unsupported.json()["detail"]["code"] == "CANDIDATE_SUBMISSION_CATEGORY_UNSUPPORTED"

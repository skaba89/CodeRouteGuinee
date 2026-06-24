from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from tests.conftest import get_admin_headers, get_center_headers
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_question import Question
from app.models_session import ExamSession


def _seed_exam_context() -> tuple[str, str]:
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    try:
        # Nettoyer toutes les questions existantes pour l'isolation
        # (évite la contamination par seed_questions de test_coverage_v5)
        from sqlalchemy import delete as _delete
        db.execute(_delete(Question))
        db.flush()
        center = Center(
            code=f"CTR-EXAM-{suffix}",
            name="Centre Examen E2E",
            city="Conakry",
            address="Corniche",
            capacity=20,
            max_sessions_per_week=3,
            status="accredited",
        )
        db.add(center)
        db.commit()
        db.refresh(center)

        session = ExamSession(
            reference=f"GN-SESSION-EXAM-{suffix}",
            center_id=center.id,
            starts_at=datetime.now(UTC) + timedelta(days=7),
            capacity=20,
        )
        db.add(session)

        candidate = Candidate(
            first_name="Aissatou",
            last_name=f"Exam-{suffix}",
            identity_number=f"ID-EXAM-{suffix}",
            phone="+224623000000",
            permit_category="B",
            reference=f"GN-CODE-EXAM-{suffix}",
        )
        db.add(candidate)

        for index in range(40):
            db.add(
                Question(
                    category="signalisation",
                    text=f"Question E2E {suffix}-{index}",
                    options=["A", "B", "C", "D"],
                    correct_answer="A",
                    explanation="Reponse de test",
                )
            )

        db.commit()
        db.refresh(candidate)
        db.refresh(session)
        return candidate.id, session.id
    finally:
        db.close()


def test_exam_scoring_certificate_and_public_verification_end_to_end() -> None:
    candidate_id, session_id = _seed_exam_context()

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)
        start_response = client.post(
            "/api/v1/exams/start",
            headers=center_headers,
            json={"candidate_id": candidate_id, "session_id": session_id},
        )
        assert start_response.status_code == 201
        attempt = start_response.json()
        assert attempt["status"] == "started"

        # Récupérer les questions VIA L'API de cet examen spécifique
        q_response = client.get(
            f"/api/v1/exams/{attempt['id']}/questions",
            headers=center_headers,
        )
        assert q_response.status_code == 200
        exam_questions = q_response.json()["questions"]
        # Construire les réponses : utiliser la première option comme réponse
        answers = {q["id"]: q["options"][0] for q in exam_questions}
        assert len(answers) >= 40

        submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=center_headers,
            json={"answers": answers},
        )
        assert submit_response.status_code == 200
        submitted_attempt = submit_response.json()
        assert submitted_attempt["status"] == "submitted"
        assert submitted_attempt["score"] >= 35
        assert submitted_attempt["passed"] is True

        duplicate_submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=center_headers,
            json={"answers": answers},
        )
        assert duplicate_submit_response.status_code == 409

        certificate_response = client.get(f"/api/v1/exams/{attempt['id']}/certificate.pdf", headers=admin_headers)
        assert certificate_response.status_code == 200
        assert certificate_response.content.startswith(b"%PDF")

        verification_response = client.get(f"/api/v1/exams/{attempt['id']}/certificate/verify")
        assert verification_response.status_code == 200
        verification = verification_response.json()
        assert verification["valid"] is True
        assert verification["attempt_id"] == attempt["id"]
        assert verification["passed"] is True
        assert verification["score"] >= 35

        summary_response = client.get("/api/v1/exams/summary", headers=admin_headers)
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["submitted_attempts"] >= 1
        assert summary["passed_attempts"] >= 1

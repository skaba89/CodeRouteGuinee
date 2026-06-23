"""
Tests E2E pour les nouveaux endpoints examen :
  GET /exams/{id}/status
  GET /exams/{id}/questions
  GET /exams/{id}/results
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_center import Center
from app.models_session import ExamSession
from tests.conftest import get_admin_headers, get_center_headers
from datetime import datetime, timedelta, UTC


def _seed_center_session_question_base():
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    try:
        center = Center(
            code=f"CTR-ENE-{suffix}",
            name=f"Centre ENE {suffix}",
            city="Conakry",
            address="Test",
            capacity=10,
            max_sessions_per_week=3,
            status="accredited",
        )
        db.add(center)
        db.commit()
        db.refresh(center)
        session = ExamSession(
            reference=f"GN-ENE-{suffix}",
            center_id=center.id,
            starts_at=datetime.now(UTC) + timedelta(days=3),
            capacity=10,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return center.id, session.id
    finally:
        db.close()


def test_exam_status_endpoint() -> None:
    """GET /exams/{id}/status retourne le statut temps réel."""
    center_id, session_id = _seed_center_session_question_base()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)

        # Créer un candidat
        cand = client.post("/api/v1/candidates", headers=admin_headers, json={
            "first_name": "Test", "last_name": f"Status-{suffix}",
            "identity_number": f"ID-STATUS-{suffix}", "phone": "+224620000001",
            "permit_category": "B",
        }).json()

        # Démarrer un examen
        attempt = client.post("/api/v1/exams/start", headers=center_headers, json={
            "candidate_id": cand["id"], "session_id": session_id,
        }).json()
        assert attempt.get("id"), f"Attempt sans ID: {attempt}"

        # GET /status
        status_resp = client.get(f"/api/v1/exams/{attempt['id']}/status", headers=admin_headers)
        assert status_resp.status_code == 200
        status = status_resp.json()
        assert status["attempt_id"] == attempt["id"]
        assert status["status"] == "started"
        assert status["remaining_seconds"] > 0
        assert status["total_seconds"] == 1800  # 30 min
        assert status["question_count"] > 0
        assert status["expired"] is False


def test_exam_questions_endpoint() -> None:
    """GET /exams/{id}/questions retourne les questions sans bonnes réponses."""
    center_id, session_id = _seed_center_session_question_base()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)

        cand = client.post("/api/v1/candidates", headers=admin_headers, json={
            "first_name": "Test", "last_name": f"Questions-{suffix}",
            "identity_number": f"ID-QUEST-{suffix}", "phone": "+224620000002",
            "permit_category": "B",
        }).json()

        attempt = client.post("/api/v1/exams/start", headers=center_headers, json={
            "candidate_id": cand["id"], "session_id": session_id,
        }).json()

        # GET /questions
        q_resp = client.get(f"/api/v1/exams/{attempt['id']}/questions", headers=admin_headers)
        assert q_resp.status_code == 200
        resp_data = q_resp.json()
        # Endpoint retourne ExamQuestionsRead avec champ "questions"
        questions = resp_data["questions"] if isinstance(resp_data, dict) else resp_data
        assert isinstance(questions, list)
        assert len(questions) > 0

        # Vérifier que les bonnes réponses ne sont PAS exposées
        for q in questions:
            assert "correct_answer" not in q or q["correct_answer"] is None, \
                "La bonne réponse ne doit pas être exposée pendant l'examen"
            assert "number" in q
            assert "text" in q
            assert "options" in q
            assert "category" in q


def test_exam_results_endpoint() -> None:
    """GET /exams/{id}/results retourne la correction détaillée après soumission."""
    center_id, session_id = _seed_center_session_question_base()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)

        cand = client.post("/api/v1/candidates", headers=admin_headers, json={
            "first_name": "Test", "last_name": f"Results-{suffix}",
            "identity_number": f"ID-RES-{suffix}", "phone": "+224620000003",
            "permit_category": "B",
        }).json()

        attempt = client.post("/api/v1/exams/start", headers=center_headers, json={
            "candidate_id": cand["id"], "session_id": session_id,
        }).json()

        # GET /questions pour récupérer les IDs
        q_data = client.get(
            f"/api/v1/exams/{attempt['id']}/questions", headers=admin_headers
        ).json()
        questions = q_data["questions"] if isinstance(q_data, dict) else q_data

        # Soumettre les réponses (première option pour chaque question)
        answers = {q["id"]: q["options"][0] for q in questions}
        submit = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=center_headers,
            json={"answers": answers},
        )
        assert submit.status_code == 200

        # GET /results
        results_resp = client.get(
            f"/api/v1/exams/{attempt['id']}/results", headers=admin_headers
        )
        assert results_resp.status_code == 200
        results = results_resp.json()
        assert results["attempt_id"] == attempt["id"]
        assert "score" in results
        assert "passed" in results
        assert "threshold" in results
        assert "questions" in results
        assert len(results["questions"]) > 0

        # Vérifier que chaque question a correct_answer ET explanation
        for q in results["questions"]:
            assert "correct_answer" in q
            assert "given_answer" in q
            assert "is_correct" in q
            assert isinstance(q["is_correct"], bool)


def test_exam_results_blocked_before_submission() -> None:
    """GET /results retourne 409 si l'examen n'est pas soumis."""
    center_id, session_id = _seed_center_session_question_base()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)

        cand = client.post("/api/v1/candidates", headers=admin_headers, json={
            "first_name": "Test", "last_name": f"Block-{suffix}",
            "identity_number": f"ID-BLK-{suffix}", "phone": "+224620000004",
            "permit_category": "B",
        }).json()

        attempt = client.post("/api/v1/exams/start", headers=center_headers, json={
            "candidate_id": cand["id"], "session_id": session_id,
        }).json()

        # Tenter de lire les résultats avant soumission
        r = client.get(f"/api/v1/exams/{attempt['id']}/results", headers=admin_headers)
        assert r.status_code == 409


def test_exam_questions_blocked_after_submission() -> None:
    """GET /questions retourne 409 si l'examen est soumis."""
    center_id, session_id = _seed_center_session_question_base()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)

        cand = client.post("/api/v1/candidates", headers=admin_headers, json={
            "first_name": "Test", "last_name": f"PostSub-{suffix}",
            "identity_number": f"ID-PSB-{suffix}", "phone": "+224620000005",
            "permit_category": "B",
        }).json()

        attempt = client.post("/api/v1/exams/start", headers=center_headers, json={
            "candidate_id": cand["id"], "session_id": session_id,
        }).json()

        q_resp3 = client.get(
            f"/api/v1/exams/{attempt['id']}/questions", headers=admin_headers
        ).json()
        questions3 = q_resp3["questions"] if isinstance(q_resp3, dict) else q_resp3
        answers = {q["id"]: q["options"][0] for q in questions3}
        client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=center_headers,
            json={"answers": answers},
        )

        # Tenter de lire les questions après soumission
        r = client.get(f"/api/v1/exams/{attempt['id']}/questions", headers=admin_headers)
        assert r.status_code == 409

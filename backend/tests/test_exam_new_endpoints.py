"""
Tests E2E pour les nouveaux endpoints examen :
  GET /exams/{id}/status
  GET /exams/{id}/questions
  GET /exams/{id}/results

Chaque examen est démarré par le parcours officiel (identité vérifiée,
réservation payée, entrée contrôlée, banque média homologuée).
"""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers, prepare_checked_in_booking, seed_media_ready_official_bank


def _started_attempt(client: TestClient) -> tuple[dict, dict[str, str]]:
    headers = get_admin_headers(client)
    seed_media_ready_official_bank(client, headers)
    ready = prepare_checked_in_booking(client, headers)
    response = client.post("/api/v1/exams/start-from-booking", headers=headers,
                           json={"booking_reference": ready["booking"]["reference"]})
    assert response.status_code == 201, response.text
    return response.json(), headers


def _submit_first_options(client: TestClient, attempt_id: str, headers: dict[str, str]) -> None:
    questions = client.get(f"/api/v1/exams/{attempt_id}/questions", headers=headers).json()["questions"]
    submit = client.post(f"/api/v1/exams/{attempt_id}/submit", headers=headers,
                         json={"answers": {q["id"]: q["options"][0] for q in questions}})
    assert submit.status_code == 200, submit.text


def test_exam_status_endpoint() -> None:
    """GET /exams/{id}/status retourne le statut temps réel."""
    with TestClient(app) as client:
        attempt, headers = _started_attempt(client)

        status_resp = client.get(f"/api/v1/exams/{attempt['id']}/status", headers=headers)
        assert status_resp.status_code == 200
        status = status_resp.json()
        assert status["attempt_id"] == attempt["id"]
        assert status["status"] == "started"
        assert status["remaining_seconds"] > 0
        assert status["total_seconds"] == 1800  # 30 min
        assert status["question_count"] == 40
        assert status["expired"] is False


def test_exam_questions_endpoint() -> None:
    """GET /exams/{id}/questions retourne les questions sans bonnes réponses."""
    with TestClient(app) as client:
        attempt, headers = _started_attempt(client)

        q_resp = client.get(f"/api/v1/exams/{attempt['id']}/questions", headers=headers)
        assert q_resp.status_code == 200
        questions = q_resp.json()["questions"]
        assert len(questions) == 40

        for q in questions:
            assert "correct_answer" not in q or q["correct_answer"] is None, \
                "La bonne réponse ne doit pas être exposée pendant l'examen"
            assert "number" in q
            assert "text" in q
            assert "options" in q
            assert "category" in q


def test_exam_results_endpoint() -> None:
    """GET /exams/{id}/results retourne la correction détaillée après soumission."""
    with TestClient(app) as client:
        attempt, headers = _started_attempt(client)
        _submit_first_options(client, attempt["id"], headers)

        results_resp = client.get(f"/api/v1/exams/{attempt['id']}/results", headers=headers)
        assert results_resp.status_code == 200
        results = results_resp.json()
        assert results["attempt_id"] == attempt["id"]
        assert "score" in results
        assert "passed" in results
        assert "threshold" in results
        assert len(results["questions"]) == 40

        for q in results["questions"]:
            assert "correct_answer" in q
            assert "given_answer" in q
            assert "is_correct" in q
            assert isinstance(q["is_correct"], bool)


def test_exam_results_blocked_before_submission() -> None:
    """GET /results retourne 409 si l'examen n'est pas soumis."""
    with TestClient(app) as client:
        attempt, headers = _started_attempt(client)

        r = client.get(f"/api/v1/exams/{attempt['id']}/results", headers=headers)
        assert r.status_code == 409


def test_exam_questions_blocked_after_submission() -> None:
    """GET /questions retourne 409 si l'examen est soumis."""
    with TestClient(app) as client:
        attempt, headers = _started_attempt(client)
        _submit_first_options(client, attempt["id"], headers)

        r = client.get(f"/api/v1/exams/{attempt['id']}/questions", headers=headers)
        assert r.status_code == 409

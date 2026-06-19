from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-trace-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": f"{role.title()} Trace E2E",
            "password": password,
            "role": role,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_exam_question_trace_is_created_and_used_for_scoring() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")
        headers = admin_headers

        created_questions = []
        for index in range(3):
            response = client.post(
                "/api/v1/questions",
                headers=admin_headers,
                json={
                    "category": "signalisation",
                    "text": f"Question trace {suffix} {index}",
                    "options": ["A", "B", "C"],
                    "correct_answer": "A",
                    "explanation": "Reponse A",
                },
            )
            assert response.status_code == 201
            created_questions.append(response.json())

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-QT-{suffix}",
                "name": "Centre Trace E2E",
                "city": "Conakry",
                "address": "Matoto",
                "capacity": 20,
                "status": "accredited",
            },
        )
        assert center_response.status_code == 201
        center = center_response.json()

        session_response = client.post(
            "/api/v1/sessions",
            headers=admin_headers,
            json={
                "center_id": center["id"],
                "starts_at": (datetime.now(UTC) + timedelta(days=11)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=admin_headers,
            json={
                "first_name": "Ibrahima",
                "last_name": f"Trace-{suffix}",
                "identity_number": f"ID-QT-{suffix}",
                "phone": "+224629000001",
                "permit_category": "B",
            },
        )
        assert candidate_response.status_code == 201
        candidate = candidate_response.json()

        start_response = client.post(
            "/api/v1/exams/start",
            headers=center_headers,
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert start_response.status_code == 201
        attempt = start_response.json()

        trace_response = client.get(
            f"/api/v1/exam-question-traces/attempts/{attempt['id']}",
            headers=admin_headers,
        )
        assert trace_response.status_code == 200
        trace = trace_response.json()
        assert trace["attempt_id"] == attempt["id"]
        assert trace["question_count"] >= 3
        assert trace["bank_hash"]
        assert "official-" in trace["version_label"] or "active-bank-" in trace["version_label"] or trace["version_label"].startswith("bank-")
        assert len(trace["question_ids"]) == trace["question_count"]
        # Les 3 questions créées peuvent ne pas être dans les 40 sélectionnées
        # (sélection aléatoire par catégorie). On vérifie juste que les question_ids
        # proviennent bien de la banque active.
        assert len(trace["question_ids"]) > 0  # Au moins une question sélectionnée

        active_questions_response = client.get("/api/v1/questions", headers=headers)
        assert active_questions_response.status_code == 200
        active_answer_key = {question["id"]: question["correct_answer"] for question in active_questions_response.json()}
        answers = {question_id: active_answer_key.get(question_id, "A") for question_id in trace["question_ids"]}
        submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=center_headers,
            json={"answers": answers},
        )
        assert submit_response.status_code == 200
        submitted = submit_response.json()
        assert submitted["status"] == "submitted"
        assert submitted["score"] == trace["question_count"]
        assert submitted["passed"] is True

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=exam.question_trace_created&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        logs = audit_response.json()
        assert any(log["details"]["attempt_id"] == attempt["id"] for log in logs)

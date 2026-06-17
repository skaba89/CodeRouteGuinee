from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-question-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Banque Questions", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def _question(client: TestClient, headers: dict[str, str]) -> dict:
    suffix = str(uuid4())[:8]
    response = client.post(
        "/api/v1/questions",
        headers=headers,
        json={
            "category": "signalisation",
            "text": f"Question gouvernance {suffix}",
            "options": ["S'arreter", "Passer"],
            "correct_answer": "S'arreter",
            "explanation": "Le feu rouge impose l'arret.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_question_governance_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/question-governance")

    assert response.status_code == 401


def test_admin_can_suspend_and_republish_question_with_audit_log() -> None:
    with TestClient(app) as client:
        headers = _admin_headers(client)
        question = _question(client, headers)

        suspended = client.post(
            f"/api/v1/question-governance/{question['id']}/decision",
            headers=headers,
            json={"status": "suspended", "reason": "Question retiree pour revue pedagogique"},
        )
        assert suspended.status_code == 200
        assert suspended.json()["latest_status"] == "suspended"
        assert suspended.json()["is_active"] is False

        active_questions = client.get("/api/v1/questions").json()
        assert all(item["id"] != question["id"] for item in active_questions)

        published = client.post(
            f"/api/v1/question-governance/{question['id']}/decision",
            headers=headers,
            json={"status": "published", "reason": "Question validee par la commission nationale"},
        )
        assert published.status_code == 200
        assert published.json()["latest_status"] == "published"
        assert published.json()["is_active"] is True

        governance = client.get("/api/v1/question-governance", headers=headers)
        assert governance.status_code == 200
        assert any(item["question_id"] == question["id"] for item in governance.json())

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.entity == "question")
                .where(AuditLog.entity_id == question["id"])
                .where(AuditLog.action == "question_governance.published")
            )
            assert audit_log is not None
            assert audit_log.details["new_active"] is True

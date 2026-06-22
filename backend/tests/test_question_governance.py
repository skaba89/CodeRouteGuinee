from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog
from app.models_question import Question


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


def test_question_official_import_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/questions/import-official",
            json={
                "source": "Commission nationale",
                "reason": "Import initial",
                "questions": [
                    {
                        "category": "signalisation",
                        "text": "Que signifie un feu rouge fixe ?",
                        "options": ["S'arreter", "Passer avec prudence"],
                        "correct_answer": "S'arreter",
                        "explanation": "Le feu rouge impose l'arret.",
                        "is_active": True,
                    }
                ],
            },
        )

    assert response.status_code == 401


def test_admin_can_import_official_questions_with_audit_log() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        question_text = f"Question officielle priorite {suffix}"

        response = client.post(
            "/api/v1/questions/import-official",
            headers=headers,
            json={
                "source": "Commission nationale du code",
                "reason": "Chargement banque pilote",
                "questions": [
                    {
                        "category": "priorite",
                        "text": question_text,
                        "options": ["Priorite a droite", "Priorite a gauche", "Arret obligatoire"],
                        "correct_answer": "Priorite a droite",
                        "explanation": "En absence de signalisation, la priorite a droite s applique.",
                        "is_active": True,
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["imported"] == 1
        assert payload["created"] == 1
        question_id = payload["question_ids"][0]

        update_response = client.post(
            "/api/v1/questions/import-official",
            headers=headers,
            json={
                "source": "Commission nationale du code",
                "reason": "Correction explication",
                "questions": [
                    {
                        "category": "priorite",
                        "text": question_text,
                        "options": ["Priorite a droite", "Priorite a gauche", "Arret obligatoire"],
                        "correct_answer": "Priorite a droite",
                        "explanation": "Regle generale de priorite hors signalisation contraire.",
                        "is_active": False,
                    }
                ],
            },
        )

        assert update_response.status_code == 200
        assert update_response.json()["updated"] == 1
        assert update_response.json()["question_ids"] == [question_id]

        governance = client.get("/api/v1/question-governance", headers=headers)
        imported = next(item for item in governance.json() if item["question_id"] == question_id)
        assert imported["is_active"] is False

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.action == "question.official_import")
                .where(AuditLog.entity == "question")
                .order_by(AuditLog.created_at.desc())
            )
            assert audit_log is not None
            assert audit_log.details["source"] == "Commission nationale du code"
            assert audit_log.details["imported"] == 1


def test_question_official_import_dry_run_does_not_write() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        question_text = f"Question simulation import {suffix}"
        headers = _admin_headers(client)

        response = client.post(
            "/api/v1/questions/import-official",
            headers=headers,
            json={
                "source": "Commission nationale du code",
                "reason": "Simulation banque officielle",
                "dry_run": True,
                "questions": [
                    {
                        "category": "signalisation",
                        "text": question_text,
                        "options": ["S'arreter", "Passer avec prudence"],
                        "correct_answer": "S'arreter",
                        "explanation": "Le conducteur doit s'arreter.",
                        "is_active": True,
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["dry_run"] is True
        assert payload["created"] == 1
        assert payload["updated"] == 0

        with SessionLocal() as db:
            question = db.scalar(select(Question).where(Question.text == question_text))
            assert question is None


def test_question_official_import_rejects_invalid_payload() -> None:
    with TestClient(app) as client:
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/questions/import-official",
            headers=headers,
            json={
                "source": "Commission nationale",
                "reason": "Rejet reponse invalide",
                "questions": [
                    {
                        "category": "signalisation",
                        "text": "Quel panneau impose l arret complet au conducteur ?",
                        "options": ["Cedez le passage", "Sens interdit"],
                        "correct_answer": "Stop",
                        "explanation": "La bonne reponse doit etre dans les options.",
                        "is_active": True,
                    }
                ],
            },
        )
        assert response.status_code == 422
        assert "Correct answer" in str(response.json()["detail"])

        duplicate = client.post(
            "/api/v1/questions/import-official",
            headers=headers,
            json={
                "source": "Commission nationale",
                "reason": "Rejet doublon",
                "questions": [
                    {
                        "category": "signalisation",
                        "text": "Que signifie un feu rouge fixe sur la chaussee ?",
                        "options": ["S'arreter", "Passer"],
                        "correct_answer": "S'arreter",
                        "is_active": True,
                    },
                    {
                        "category": "Signalisation",
                        "text": "Que signifie un feu rouge fixe sur la chaussee ?",
                        "options": ["S'arreter", "Passer"],
                        "correct_answer": "S'arreter",
                        "is_active": True,
                    },
                ],
            },
        )
        assert duplicate.status_code == 422
        assert "Duplicate questions" in str(duplicate.json()["detail"])


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

        active_questions = client.get("/api/v1/questions", headers=headers).json()["items"]
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

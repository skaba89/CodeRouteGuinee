"""Un import officiel ne peut pas modifier une question validée sans la renvoyer
en validation.

Régression : l'import réécrivait texte, options, bonne réponse et média d'une
question `approved` en conservant ce statut. Une nouvelle correction devenait
officielle sans relecture ni approbation (quatre yeux contournés).
"""
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog
from app.models_question import Question
from tests.conftest import get_admin_headers


def _row(text: str, correct: str = "S'arrêter", **extra) -> dict:
    return {
        "category": "signalisation",
        "text": text,
        "options": ["S'arrêter", "Passer avec prudence", "Klaxonner"],
        "correct_answer": correct,
        "explanation": "Le feu rouge impose l'arrêt.",
        "is_active": True,
        **extra,
    }


def _import(client: TestClient, headers: dict, rows: list[dict], dry_run: bool = False) -> dict:
    response = client.post("/api/v1/questions/import-official", headers=headers, json={
        "source": "Commission nationale du code", "reason": "Test revalidation",
        "dry_run": dry_run, "questions": rows,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _approved_question(client: TestClient, headers: dict, text: str) -> str:
    question_id = _import(client, headers, [_row(text)])["question_ids"][0]
    approved = client.post(f"/api/v1/questions/{question_id}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    return question_id


def _question(question_id: str) -> Question:
    with SessionLocal() as db:
        question = db.get(Question, question_id)
        db.expunge(question)
        return question


def test_changed_correct_answer_returns_approved_question_to_draft() -> None:
    text = f"Feu rouge fixe {uuid4().hex[:8]} ?"
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        question_id = _approved_question(client, headers, text)
        before = _question(question_id)

        result = _import(client, headers, [_row(text, correct="Passer avec prudence")])

    assert result["returned_to_validation"] == 1
    assert result["returned_to_validation_ids"] == [question_id]
    after = _question(question_id)
    assert after.correct_answer == "Passer avec prudence"
    assert after.validation_status == "draft"
    assert after.validated_by is None and after.validated_at is None
    assert after.version == before.version + 1
    with SessionLocal() as db:
        audit = db.query(AuditLog).filter(
            AuditLog.action == "question.returned_to_validation",
            AuditLog.entity_id == question_id,
        ).one()
    assert audit.details["previous_status"] == "approved"


def test_identical_reimport_keeps_approval() -> None:
    text = f"Feu rouge fixe {uuid4().hex[:8]} ?"
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        question_id = _approved_question(client, headers, text)

        result = _import(client, headers, [_row(text)])

    assert result["returned_to_validation"] == 0
    after = _question(question_id)
    assert after.validation_status == "approved"
    assert after.validated_by is not None


def test_changed_media_or_options_also_require_revalidation() -> None:
    text_options = f"Options {uuid4().hex[:8]} ?"
    text_media = f"Média {uuid4().hex[:8]} ?"
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        options_id = _approved_question(client, headers, text_options)
        media_id = _approved_question(client, headers, text_media)

        changed_options = _row(text_options)
        changed_options["options"] = ["S'arrêter", "Accélérer"]
        changed_media = _row(text_media, media_type="image",
                             media_url="https://cdn.example.com/coderoute-tests/feu-rouge.webp",
                             media_alt="Feu rouge à un carrefour")
        result = _import(client, headers, [changed_options, changed_media])

    assert sorted(result["returned_to_validation_ids"]) == sorted([options_id, media_id])
    assert _question(options_id).validation_status == "draft"
    assert _question(media_id).validation_status == "draft"


def test_dry_run_reports_revalidation_without_changing_anything() -> None:
    text = f"Feu rouge fixe {uuid4().hex[:8]} ?"
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        question_id = _approved_question(client, headers, text)

        preview = _import(client, headers, [_row(text, correct="Klaxonner")], dry_run=True)

    assert preview["dry_run"] is True
    assert preview["returned_to_validation_ids"] == [question_id]
    after = _question(question_id)
    assert after.validation_status == "approved"
    assert after.correct_answer == "S'arrêter"


def test_modified_question_leaves_official_exam_pool() -> None:
    """Une question renvoyée en brouillon n'est plus éligible à l'examen officiel."""
    text = f"Feu rouge fixe {uuid4().hex[:8]} ?"
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        question_id = _approved_question(client, headers, text)
        _import(client, headers, [_row(text, correct="Klaxonner")])

    with SessionLocal() as db:
        approved_ids = {
            row.id for row in db.query(Question).filter(
                Question.is_active.is_(True), Question.validation_status == "approved",
            )
        }
    assert question_id not in approved_ids

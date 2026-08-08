"""Non-régression — médias internes lisibles, écritures externes strictes."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas import QuestionCreate, QuestionMediaUpdate, QuestionRead


def _read_payload(media_type: str) -> dict:
    return {
        "id": "question-1",
        "category": "signalisation",
        "text": "Que signifie ce panneau ?",
        "options": ["STOP", "Cédez le passage"],
        "correct_answer": "STOP",
        "explanation": "Arrêt obligatoire.",
        "media_type": media_type,
        "media_url": "stop" if media_type == "sign" else "intersection_priority_right",
        "media_alt": "Visuel interne contrôlé",
        "is_active": True,
        "validation_status": "approved",
        "validated_by": None,
        "validated_at": None,
        "rejection_reason": None,
        "version": 1,
        "translations": None,
        "created_at": datetime(2026, 8, 8, 12, 0, 0),
    }


def test_question_read_accepts_internal_sign_media():
    question = QuestionRead.model_validate(_read_payload("sign"))
    assert question.media_type == "sign"
    assert question.media_url == "stop"


def test_question_read_accepts_internal_scene_media():
    question = QuestionRead.model_validate(_read_payload("scene"))
    assert question.media_type == "scene"


def test_question_create_still_rejects_internal_sign_as_external_upload():
    with pytest.raises(ValidationError):
        QuestionCreate(
            category="signalisation",
            text="Question de test",
            options=["A", "B"],
            correct_answer="A",
            media_type="sign",
            media_url="stop",
        )


def test_question_media_update_still_rejects_internal_scene_as_external_upload():
    with pytest.raises(ValidationError):
        QuestionMediaUpdate(
            media_type="scene",
            media_url="https://cdn.coderoute.example/scene.webp",
        )

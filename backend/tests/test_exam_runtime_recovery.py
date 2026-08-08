"""Tests ciblés — reprise serveur des réponses d'un examen officiel."""
from __future__ import annotations

from types import SimpleNamespace

from app.routers.exam_runtime import _sanitize_trace_answers


def _trace(question_ids: list[str] | None = None):
    return SimpleNamespace(question_ids=question_ids or ["q-1", "q-2"])


def test_server_answer_recovery_keeps_only_questions_from_official_trace():
    answers = {
        "q-1": "Réponse A",
        "q-2": "Réponse B",
        "q-injected": "Ne doit jamais ressortir",
    }

    sanitized = _sanitize_trace_answers(_trace(), answers)

    assert sanitized == {"q-1": "Réponse A", "q-2": "Réponse B"}


def test_server_answer_recovery_rejects_non_string_answer_values():
    answers = {"q-1": "Réponse A", "q-2": {"unexpected": True}}

    sanitized = _sanitize_trace_answers(_trace(), answers)

    assert sanitized == {"q-1": "Réponse A"}


def test_server_answer_recovery_handles_empty_copy():
    assert _sanitize_trace_answers(_trace(), None) == {}
    assert _sanitize_trace_answers(_trace(), {}) == {}

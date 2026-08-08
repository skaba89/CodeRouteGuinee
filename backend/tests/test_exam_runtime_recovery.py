"""Tests ciblés — reprise serveur des réponses d'un examen officiel."""
from __future__ import annotations

from types import SimpleNamespace

from app.exam_attempt_locking import (
    RECOVERABLE_ATTEMPT_STATUSES,
    find_recoverable_attempt,
    lock_exam_attempt,
)
from app.routers.exam_runtime import _sanitize_trace_answers


def _trace(question_ids: list[str] | None = None):
    return SimpleNamespace(question_ids=question_ids or ["q-1", "q-2"])


class _CaptureScalarDb:
    def __init__(self, result=None):
        self.result = result
        self.statement = None

    def scalar(self, statement):
        self.statement = statement
        return self.result


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


def test_recoverable_attempt_statuses_are_limited_to_active_runtime_states():
    assert RECOVERABLE_ATTEMPT_STATUSES == ("started", "expired")


def test_lock_exam_attempt_uses_for_update_and_attempt_id_filter():
    marker = object()
    db = _CaptureScalarDb(marker)

    result = lock_exam_attempt(db, "attempt-123")

    assert result is marker
    sql = str(db.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "exam_attempts.id = 'attempt-123'" in sql
    assert "FOR UPDATE" in sql


def test_find_recoverable_attempt_scopes_candidate_session_status_and_lock():
    marker = object()
    db = _CaptureScalarDb(marker)

    result = find_recoverable_attempt(db, "candidate-1", "session-1")

    assert result is marker
    sql = str(db.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "exam_attempts.candidate_id = 'candidate-1'" in sql
    assert "exam_attempts.session_id = 'session-1'" in sql
    assert "exam_attempts.status IN ('started', 'expired')" in sql
    assert "ORDER BY exam_attempts.started_at DESC" in sql
    assert "FOR UPDATE" in sql

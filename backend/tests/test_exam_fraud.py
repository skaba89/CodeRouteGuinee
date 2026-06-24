from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.models_audit import AuditLog
from app.routers.exams import EXAM_DURATION_MINUTES, _is_attempt_expired, _write_exam_guard_log


class FakeDb:
    def __init__(self) -> None:
        self.items = []

    def add(self, item) -> None:
        self.items.append(item)


def test_exam_attempt_is_not_expired_before_duration_limit() -> None:
    now = datetime.now(UTC)
    attempt = SimpleNamespace(started_at=now - timedelta(minutes=EXAM_DURATION_MINUTES - 1))

    assert _is_attempt_expired(attempt, now) is False


def test_exam_attempt_is_expired_after_duration_limit() -> None:
    now = datetime.now(UTC)
    attempt = SimpleNamespace(started_at=now - timedelta(minutes=EXAM_DURATION_MINUTES + 1))

    assert _is_attempt_expired(attempt, now) is True


def test_exam_guard_log_contains_attempt_context() -> None:
    now = datetime.now(UTC)
    attempt = SimpleNamespace(
        id="attempt-1",
        candidate_id="candidate-1",
        session_id="session-1",
        status="submitted",
        started_at=now - timedelta(minutes=5),
        submitted_at=now,
    )
    db = FakeDb()

    _write_exam_guard_log(db, attempt, "exam.replay_submission", "already_submitted", now)

    assert len(db.items) == 1
    audit_log = db.items[0]
    assert isinstance(audit_log, AuditLog)
    assert audit_log.action == "exam.replay_submission"
    assert audit_log.entity == "exam_attempt"
    assert audit_log.entity_id == "attempt-1"
    assert audit_log.details["reason"] == "already_submitted"
    assert audit_log.details["candidate_id"] == "candidate-1"

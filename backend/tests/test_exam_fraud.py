from datetime import datetime, timedelta
from types import SimpleNamespace

from app.routers.exams import EXAM_DURATION_MINUTES, _is_attempt_expired


def test_exam_attempt_is_not_expired_before_duration_limit() -> None:
    now = datetime.utcnow()
    attempt = SimpleNamespace(started_at=now - timedelta(minutes=EXAM_DURATION_MINUTES - 1))

    assert _is_attempt_expired(attempt, now) is False


def test_exam_attempt_is_expired_after_duration_limit() -> None:
    now = datetime.utcnow()
    attempt = SimpleNamespace(started_at=now - timedelta(minutes=EXAM_DURATION_MINUTES + 1))

    assert _is_attempt_expired(attempt, now) is True

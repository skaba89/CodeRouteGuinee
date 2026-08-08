"""Tests de non-régression — sécurité et intégrité des tentatives d'examen."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.exam_engine import filter_official_exam_pool
from app.models_candidate import Candidate
from app.models_session import ExamSession
from app.question_bank_gn import QUESTIONS_GN, QUESTIONS_TRAINING_FULL
from app.routers.exam_runtime import _assert_runtime_access
from app.routers.exams import (
    _assert_attempt_access,
    _require_official_bank_ready,
    _require_official_trace,
)


class _FakeDb:
    def __init__(self, candidate=None, session=None):
        self.candidate = candidate
        self.session = session
        self.get_calls = 0

    def get(self, model, key):
        self.get_calls += 1
        if model is Candidate and self.candidate is not None and self.candidate.id == key:
            return self.candidate
        if model is ExamSession and self.session is not None and self.session.id == key:
            return self.session
        return None


def _attempt(candidate_id: str = "candidate-1", session_id: str = "session-1"):
    return SimpleNamespace(candidate_id=candidate_id, session_id=session_id)


def _user(
    *,
    user_id: str = "user-1",
    email: str = "candidate@test.gn",
    role: str = "candidate",
    center_id: str | None = None,
):
    return SimpleNamespace(id=user_id, email=email, role=role, center_id=center_id)


def _candidate(
    *,
    candidate_id: str = "candidate-1",
    user_id: str | None = "user-1",
    email: str | None = "candidate@test.gn",
):
    return SimpleNamespace(id=candidate_id, user_id=user_id, email=email)


def _session(*, session_id: str = "session-1", center_id: str = "center-1"):
    return SimpleNamespace(id=session_id, center_id=center_id)


def test_admin_access_does_not_require_candidate_lookup():
    db = _FakeDb()

    _assert_attempt_access(db, _user(role="admin"), _attempt())

    assert db.get_calls == 0


def test_candidate_owner_by_user_id_is_allowed():
    db = _FakeDb(_candidate(user_id="owner-user", email=None))

    _assert_attempt_access(
        db,
        _user(user_id="owner-user", email="other@test.gn"),
        _attempt(),
    )


def test_candidate_owner_by_email_is_allowed_for_legacy_accounts():
    db = _FakeDb(_candidate(user_id=None, email="legacy@test.gn"))

    _assert_attempt_access(
        db,
        _user(user_id="new-user", email="legacy@test.gn"),
        _attempt(),
    )


def test_foreign_candidate_is_rejected():
    db = _FakeDb(_candidate(user_id="owner-user", email="owner@test.gn"))

    with pytest.raises(HTTPException) as exc_info:
        _assert_attempt_access(
            db,
            _user(user_id="attacker-user", email="attacker@test.gn"),
            _attempt(),
        )

    assert exc_info.value.status_code == 403
    assert "appartient" in str(exc_info.value.detail)


def test_missing_candidate_is_rejected():
    db = _FakeDb(candidate=None)

    with pytest.raises(HTTPException) as exc_info:
        _assert_attempt_access(db, _user(), _attempt(candidate_id="missing"))

    assert exc_info.value.status_code == 403


def test_historical_center_guard_allows_own_center():
    db = _FakeDb(session=_session(center_id="center-conakry"))

    _assert_attempt_access(
        db,
        _user(role="center", center_id="center-conakry"),
        _attempt(),
    )


def test_historical_center_guard_rejects_other_center():
    db = _FakeDb(session=_session(center_id="center-kankan"))

    with pytest.raises(HTTPException) as exc_info:
        _assert_attempt_access(
            db,
            _user(role="center", center_id="center-conakry"),
            _attempt(),
        )

    assert exc_info.value.status_code == 403
    assert "autre centre" in str(exc_info.value.detail)


def test_runtime_center_can_access_its_own_session():
    db = _FakeDb(session=_session(center_id="center-conakry"))

    _assert_runtime_access(
        db,
        _user(role="center", center_id="center-conakry"),
        _attempt(),
    )


def test_runtime_center_cannot_access_another_center_session():
    db = _FakeDb(session=_session(center_id="center-kankan"))

    with pytest.raises(HTTPException) as exc_info:
        _assert_runtime_access(
            db,
            _user(role="center", center_id="center-conakry"),
            _attempt(),
        )

    assert exc_info.value.status_code == 403
    assert "autre centre" in str(exc_info.value.detail)


def test_runtime_candidate_cannot_access_foreign_attempt():
    db = _FakeDb(candidate=_candidate(user_id="owner-user", email="owner@test.gn"))

    with pytest.raises(HTTPException) as exc_info:
        _assert_runtime_access(
            db,
            _user(user_id="foreign-user", email="foreign@test.gn", role="candidate"),
            _attempt(),
        )

    assert exc_info.value.status_code == 403


def test_official_bank_accepts_exactly_40_approved_questions():
    _require_official_bank_ready([object() for _ in range(40)])


def test_official_bank_rejects_39_approved_questions():
    with pytest.raises(HTTPException) as exc_info:
        _require_official_bank_ready([object() for _ in range(39)])

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "OFFICIAL_QUESTION_BANK_NOT_READY"
    assert exc_info.value.detail["approved_questions"] == 39
    assert exc_info.value.detail["required_questions"] == 40


def test_legacy_training_question_is_excluded_even_if_approved_upstream():
    training = SimpleNamespace(id="training-1", text=QUESTIONS_TRAINING_FULL[0]["text"])
    official = SimpleNamespace(id="official-1", text="Question officielle nouvellement certifiée DNTT")

    filtered = filter_official_exam_pool([training, official])

    assert filtered == [official]


def test_seeded_200_question_dataset_reduces_to_40_official_items():
    seeded = [
        SimpleNamespace(id=f"seed-{index}", text=item["text"])
        for index, item in enumerate(QUESTIONS_GN + QUESTIONS_TRAINING_FULL)
    ]

    filtered = filter_official_exam_pool(seeded)
    official_texts = {item["text"] for item in QUESTIONS_GN}

    assert len(seeded) == 200
    assert len(filtered) == 40
    assert {item.text for item in filtered} == official_texts


def test_future_approved_official_import_remains_eligible():
    imported = SimpleNamespace(
        id="official-import-1",
        text="Question officielle importée après le seed historique",
    )

    assert filter_official_exam_pool([imported]) == [imported]


def test_missing_official_trace_is_never_reconstructed():
    with pytest.raises(HTTPException) as exc_info:
        _require_official_trace(None)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "OFFICIAL_EXAM_TRACE_MISSING"

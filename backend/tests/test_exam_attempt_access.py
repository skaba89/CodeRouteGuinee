"""Tests de non-régression — contrôle horizontal des tentatives d'examen."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models_candidate import Candidate
from app.routers.exams import _assert_attempt_access


class _FakeDb:
    def __init__(self, candidate=None):
        self.candidate = candidate
        self.get_calls = 0

    def get(self, model, key):
        self.get_calls += 1
        if model is Candidate and self.candidate is not None and self.candidate.id == key:
            return self.candidate
        return None


def _attempt(candidate_id: str = "candidate-1"):
    return SimpleNamespace(candidate_id=candidate_id)


def _user(*, user_id: str = "user-1", email: str = "candidate@test.gn", role: str = "candidate"):
    return SimpleNamespace(id=user_id, email=email, role=role)


def _candidate(*, candidate_id: str = "candidate-1", user_id: str | None = "user-1", email: str | None = "candidate@test.gn"):
    return SimpleNamespace(id=candidate_id, user_id=user_id, email=email)


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

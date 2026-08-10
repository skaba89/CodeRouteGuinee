from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from app.routers import media_library
from app.routers import media_migration_plan
from app.schemas_media_migration import MediaMigrationPlanRequest


def _question(qid="q-1"):
    return SimpleNamespace(id=qid, validation_status="approved")


def _asset(mid="m-1"):
    return SimpleNamespace(
        id=mid,
        media_type="image",
        theme="STOP",
        archived_at=None,
        usage_type="exam",
        source_type="original",
        quality_status="validated",
        regulatory_status="validated",
    )


def _ready_assessment():
    return {"passed": True, "checks": [], "blockers": []}


def _payload(*, dry_run=True, replace=False, mappings=None):
    return MediaMigrationPlanRequest(
        dry_run=dry_run,
        replace_existing=replace,
        reason="Migration contrôlée test",
        mappings=mappings or [{"question_id": "q-1", "media_id": "m-1"}],
    )


def test_media_migration_plan_dry_run_is_read_only_and_ready(monkeypatch):
    question = _question()
    asset = _asset()
    db = MagicMock()

    def fake_get(model, identifier):
        if model is Question:
            return question if identifier == "q-1" else None
        if model is MediaAsset:
            return asset if identifier == "m-1" else None
        return None

    db.get.side_effect = fake_get
    db.scalar.return_value = None
    monkeypatch.setattr(media_migration_plan, "evaluate_media_asset", lambda *_args, **_kwargs: _ready_assessment())

    result = media_migration_plan.media_migration_plan(
        payload=_payload(dry_run=True),
        db=db,
        current_user=SimpleNamespace(id="admin-1", role="admin"),
    )

    assert result["dry_run"] is True
    assert result["all_ready"] is True
    assert result["summary"]["ready_create"] == 1
    assert result["applied"] == 0
    assert result["institutional_validation_inferred"] is False
    db.commit.assert_not_called()
    db.add.assert_not_called()


def test_media_migration_plan_apply_creates_primary_atomically(monkeypatch):
    question = _question()
    asset = _asset()
    db = MagicMock()

    # Non-dry-run uses SELECT ... FOR UPDATE through db.scalar. Return question,
    # media, then no existing primary in that order.
    db.scalar.side_effect = [question, asset, None]
    monkeypatch.setattr(media_migration_plan, "evaluate_media_asset", lambda *_args, **_kwargs: _ready_assessment())

    result = media_migration_plan.media_migration_plan(
        payload=_payload(dry_run=False),
        db=db,
        current_user=SimpleNamespace(id="admin-1", role="admin"),
    )

    assert result["dry_run"] is False
    assert result["all_ready"] is True
    assert result["applied"] == 1
    assert result["summary"]["ready_create"] == 1
    assert any(isinstance(call.args[0], QuestionMedia) for call in db.add.call_args_list)
    db.commit.assert_called_once()


def test_media_migration_plan_apply_refuses_entire_batch_if_media_blocked(monkeypatch):
    question = _question()
    asset = _asset()
    db = MagicMock()
    db.scalar.side_effect = [question, asset, None]
    monkeypatch.setattr(
        media_migration_plan,
        "evaluate_media_asset",
        lambda *_args, **_kwargs: {
            "passed": False,
            "checks": [{"code": "REGULATORY_APPROVED", "passed": False}],
            "blockers": ["REGULATORY_APPROVED: regulatory_status=under_review"],
        },
    )

    with pytest.raises(HTTPException) as exc:
        media_migration_plan.media_migration_plan(
            payload=_payload(dry_run=False),
            db=db,
            current_user=SimpleNamespace(id="admin-1", role="admin"),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "MEDIA_MIGRATION_PLAN_NOT_READY"
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_media_migration_plan_replacement_requires_super_admin():
    with pytest.raises(HTTPException) as exc:
        media_migration_plan.media_migration_plan(
            payload=_payload(dry_run=True, replace=True),
            db=MagicMock(),
            current_user=SimpleNamespace(id="admin-1", role="admin"),
        )
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "MEDIA_PRIMARY_REPLACEMENT_REQUIRES_SUPER_ADMIN"


def test_media_migration_plan_rejects_duplicate_question_ids():
    payload = _payload(
        mappings=[
            {"question_id": "q-1", "media_id": "m-1"},
            {"question_id": "q-1", "media_id": "m-2"},
        ]
    )
    with pytest.raises(HTTPException) as exc:
        media_migration_plan.media_migration_plan(
            payload=payload,
            db=MagicMock(),
            current_user=SimpleNamespace(id="admin-1", role="admin"),
        )
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "DUPLICATE_QUESTION_IN_MEDIA_MIGRATION_PLAN"


def test_media_migration_plan_is_mounted_once_under_media_library_router():
    matches = [
        route
        for route in media_library.router.routes
        if getattr(route, "path", None) == "/media-library/migration-plan"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]
    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "app.routers.media_migration_plan"

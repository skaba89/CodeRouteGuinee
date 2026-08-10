from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models_audit import AuditLog
from app.models_media import QuestionMedia
from app.routers import media_library
from app.routers import media_link_guard
from app.schemas_media import QuestionMediaLinkCreate


LINK_PATH = "/media-library/questions/{question_id}/links"


def test_media_link_guard_locks_question_asset_and_exclusive_role():
    question = SimpleNamespace(id="q-1")
    asset = SimpleNamespace(id="m-1", archived_at=None)
    db = MagicMock()
    db.scalar.side_effect = [question, asset, None]

    result = media_link_guard.link_question_media_guard(
        question_id="q-1",
        payload=QuestionMediaLinkCreate(media_id="m-1", role="primary", display_order=0),
        db=db,
        current_user=SimpleNamespace(id="admin-1", role="admin"),
    )

    assert isinstance(result, QuestionMedia)
    assert result.question_id == "q-1"
    assert result.media_id == "m-1"
    assert result.role == "primary"
    assert db.scalar.call_count == 3
    for call in db.scalar.call_args_list:
        statement = call.args[0]
        assert getattr(statement, "_for_update_arg", None) is not None
    audits = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], AuditLog)]
    assert len(audits) == 1
    assert audits[0].details["concurrency_guard"] == "question_row_lock"
    db.commit.assert_called_once()


def test_media_link_guard_rejects_competing_primary_before_insert():
    question = SimpleNamespace(id="q-1")
    asset = SimpleNamespace(id="m-2", archived_at=None)
    occupied = SimpleNamespace(id="link-old", media_id="m-1")
    db = MagicMock()
    db.scalar.side_effect = [question, asset, occupied]

    with pytest.raises(HTTPException) as exc:
        media_link_guard.link_question_media_guard(
            question_id="q-1",
            payload=QuestionMediaLinkCreate(media_id="m-2", role="primary", display_order=0),
            db=db,
            current_user=SimpleNamespace(id="admin-1", role="admin"),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["link_id"] == "link-old"
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_manual_media_link_route_is_replaced_once_by_concurrency_guard():
    matches = [
        route
        for route in media_library.router.routes
        if getattr(route, "path", None) == LINK_PATH
        and "POST" in (getattr(route, "methods", set()) or set())
    ]
    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "app.routers.media_link_guard"
    assert matches[0].endpoint.__name__ == "link_question_media_guard"

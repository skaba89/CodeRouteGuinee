from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.routers import media_library
from app.routers import media_migration_queue


def _question(qid: str, *, status: str, media_type=None, media_url=None):
    return SimpleNamespace(
        id=qid,
        category="Signalisation",
        text=f"Question {qid}",
        validation_status=status,
        is_active=True,
        media_type=media_type,
        media_url=media_url,
    )


def test_media_migration_queue_prioritizes_approved_blockers_and_never_exposes_answers(monkeypatch):
    q_blocked = _question("q-blocked", status="approved", media_type="scene", media_url="legacy-scene")
    q_legacy = _question("q-legacy", status="approved", media_type="sign", media_url="stop")
    q_none = _question("q-none", status="draft")
    q_publishable = _question("q-ready", status="approved")

    blocked_asset = SimpleNamespace(
        id="media-blocked",
        media_type="video",
        theme="GIRATOIRE",
        source_type="internal",
        quality_status="validated",
        regulatory_status="under_review",
    )
    ready_asset = SimpleNamespace(
        id="media-ready",
        media_type="image",
        theme="STOP",
        source_type="original",
        quality_status="validated",
        regulatory_status="validated",
    )

    scalar_result = MagicMock()
    scalar_result.all.return_value = [q_blocked, q_legacy, q_none, q_publishable]
    link_result = MagicMock()
    link_result.all.return_value = [
        ("q-blocked", blocked_asset),
        ("q-ready", ready_asset),
    ]

    db = MagicMock()
    db.scalars.return_value = scalar_result
    db.execute.return_value = link_result

    def fake_evaluate(_db, asset, **_kwargs):
        if asset.id == "media-ready":
            return {"passed": True, "checks": [], "blockers": []}
        return {
            "passed": False,
            "checks": [
                {"code": "VIDEO_POSTER_VALIDATED", "passed": False},
                {"code": "REGULATORY_APPROVED", "passed": False},
            ],
            "blockers": [
                "VIDEO_POSTER_VALIDATED: poster image validé obligatoire",
                "REGULATORY_APPROVED: regulatory_status=under_review; authority_ref=absente",
            ],
        }

    monkeypatch.setattr(media_migration_queue, "evaluate_media_asset", fake_evaluate)

    result = media_migration_queue.media_migration_queue(
        state_filter="needs_action",
        category=None,
        question_status=None,
        search=None,
        limit=50,
        offset=0,
        db=db,
        _current_user=SimpleNamespace(role="admin", id="admin-1"),
    )

    assert result["total"] == 3
    assert result["matched_questions"] == 4
    assert result["counts_by_state"] == {
        "publishable": 1,
        "normalized_blocked": 1,
        "legacy_only": 1,
        "no_media": 1,
    }
    assert [item["question_id"] for item in result["items"]][0] == "q-blocked"
    blocked = result["items"][0]
    assert blocked["queue_state"] == "normalized_blocked"
    assert blocked["priority"] == "official_first"
    assert blocked["blocker_codes"] == ["VIDEO_POSTER_VALIDATED", "REGULATORY_APPROVED"]
    assert blocked["primary_media"]["id"] == "media-blocked"
    assert all("correct_answer" not in item for item in result["items"])
    assert result["institutional_validation_inferred"] is False


def test_media_migration_queue_can_filter_publishable(monkeypatch):
    ready = _question("q-ready", status="approved")
    asset = SimpleNamespace(
        id="media-ready",
        media_type="image",
        theme="STOP",
        source_type="original",
        quality_status="validated",
        regulatory_status="validated",
    )
    scalar_result = MagicMock()
    scalar_result.all.return_value = [ready]
    link_result = MagicMock()
    link_result.all.return_value = [("q-ready", asset)]
    db = MagicMock()
    db.scalars.return_value = scalar_result
    db.execute.return_value = link_result
    monkeypatch.setattr(
        media_migration_queue,
        "evaluate_media_asset",
        lambda *_args, **_kwargs: {"passed": True, "checks": [], "blockers": []},
    )

    result = media_migration_queue.media_migration_queue(
        state_filter="publishable",
        category=None,
        question_status=None,
        search=None,
        limit=50,
        offset=0,
        db=db,
        _current_user=SimpleNamespace(role="admin", id="admin-1"),
    )
    assert result["total"] == 1
    assert result["items"][0]["queue_state"] == "publishable"


def test_media_migration_queue_rejects_unknown_state():
    with pytest.raises(HTTPException) as exc:
        media_migration_queue.media_migration_queue(
            state_filter="magic",
            category=None,
            question_status=None,
            search=None,
            limit=50,
            offset=0,
            db=MagicMock(),
            _current_user=SimpleNamespace(role="admin", id="admin-1"),
        )
    assert exc.value.status_code == 422


def test_media_migration_queue_is_mounted_once_under_media_library_router():
    matches = [
        route
        for route in media_library.router.routes
        if getattr(route, "path", None) == "/media-library/migration-queue"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]
    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "app.routers.media_migration_queue"

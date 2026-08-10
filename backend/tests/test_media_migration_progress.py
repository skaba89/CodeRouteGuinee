from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.routers import media_library
from app.routers import media_migration_progress


def test_media_migration_progress_counts_real_state_without_institutional_inference(monkeypatch):
    image = SimpleNamespace(id="media-image", media_type="image", source_type="original")
    video = SimpleNamespace(id="media-video", media_type="video", source_type="generated")

    question_result = MagicMock()
    question_result.all.return_value = [
        ("q-legacy", "sign", "stop"),
        ("q-none", None, None),
        ("q-image", "scene", "old-scene"),
        ("q-video", "scene", "old-video-scene"),
    ]
    link_result = MagicMock()
    link_result.all.return_value = [
        ("q-image", image),
        ("q-video", video),
    ]

    db = MagicMock()
    db.execute.side_effect = [question_result, link_result]

    monkeypatch.setattr(
        media_migration_progress,
        "evaluate_media_asset",
        lambda _db, asset, **_kwargs: {"passed": asset.id == "media-image"},
    )

    result = media_migration_progress.media_migration_progress(
        db=db,
        _current_user=SimpleNamespace(role="admin", id="admin-1"),
    )

    assert result["total_questions"] == 4
    assert result["normalized_primary"] == 2
    assert result["normalized_percent"] == 50.0
    assert result["publishable_premium"] == 1
    assert result["publishable_percent"] == 25.0
    assert result["normalized_blocked"] == 1
    assert result["generated_or_legacy_primary"] == 1
    assert result["legacy_only"] == 1
    assert result["no_media"] == 1
    assert result["by_primary_type"] == {"image": 1, "video": 1}
    assert result["blocked_question_ids_sample"] == ["q-video"]
    assert result["institutional_validation_inferred"] is False


def test_media_migration_progress_is_mounted_once_under_media_library_router():
    matches = [
        route
        for route in media_library.router.routes
        if getattr(route, "path", None) == "/media-library/migration-progress"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]
    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "app.routers.media_migration_progress"

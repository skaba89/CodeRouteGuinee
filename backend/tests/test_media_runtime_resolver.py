from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.db.session import SessionLocal, init_db
from app.media_runtime_resolver import resolve_exam_media, resolve_exam_media_batch
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question


@pytest.fixture(autouse=True)
def clean_runtime_media_rows():
    init_db()
    with SessionLocal() as db:
        db.execute(delete(QuestionMedia))
        db.execute(delete(MediaAsset))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(QuestionMedia))
        db.execute(delete(MediaAsset))
        db.commit()


def _question(*, legacy_type: str | None = "scene", legacy_url: str | None = "priority-right") -> Question:
    return Question(
        category="priorites",
        text=f"Question resolver {uuid4().hex}",
        options=["A", "B"],
        correct_answer="A",
        explanation="Explication",
        media_type=legacy_type,
        media_url=legacy_url,
        media_alt="Vue de la circulation",
        validation_status="approved",
        is_active=True,
    )


def _image(*, quality="validated", regulatory="validated") -> MediaAsset:
    return MediaAsset(
        media_type="image",
        usage_type="exam",
        secure_url=f"https://media.coderoute.example/{uuid4().hex}.webp",
        mime_type="image/webp",
        width=1920,
        height=1080,
        file_size_bytes=700_000,
        checksum_sha256=uuid4().hex + uuid4().hex,
        theme="PRIORITES",
        country_code="GN",
        source_type="original",
        source_reference="CAPTATION-001",
        copyright_owner="CodeRoute Guinée",
        quality_status=quality,
        regulatory_status=regulatory,
        regulatory_authority_reference="DNTT-MEDIA-001" if regulatory == "validated" else None,
    )


def test_legacy_media_is_preserved_when_question_has_not_migrated():
    with SessionLocal() as db:
        question = _question()
        db.add(question); db.commit(); db.refresh(question)
        media = resolve_exam_media(db, question)
        assert media.source == "legacy"
        assert media.media_type == "scene"
        assert media.media_url == "priority-right"
        assert media.degraded is False


def test_validated_normalized_image_replaces_legacy_media():
    with SessionLocal() as db:
        question = _question()
        asset = _image()
        db.add_all([question, asset]); db.flush()
        db.add(QuestionMedia(question_id=question.id, media_id=asset.id, role="primary", display_order=0))
        db.commit()
        media = resolve_exam_media(db, question)
        assert media.source == "normalized"
        assert media.media_type == "image"
        assert media.media_url == asset.secure_url
        assert media.fallback_reason is None
        assert "PRIORITES" in (media.media_alt or "")


def test_unvalidated_normalized_asset_never_leaks_to_candidate_and_falls_back_legacy():
    with SessionLocal() as db:
        question = _question()
        asset = _image(quality="review_required", regulatory="under_review")
        db.add_all([question, asset]); db.flush()
        db.add(QuestionMedia(question_id=question.id, media_id=asset.id, role="primary"))
        db.commit()
        media = resolve_exam_media(db, question)
        assert media.source == "legacy"
        assert media.media_url == "priority-right"
        assert media.media_url != asset.secure_url
        assert media.degraded is True
        assert media.fallback_reason == "normalized_primary_not_publishable"


def test_invalid_normalized_asset_without_legacy_returns_controlled_none():
    with SessionLocal() as db:
        question = _question(legacy_type=None, legacy_url=None)
        asset = _image(quality="draft", regulatory="not_reviewed")
        db.add_all([question, asset]); db.flush()
        db.add(QuestionMedia(question_id=question.id, media_id=asset.id, role="primary"))
        db.commit()
        media = resolve_exam_media(db, question)
        assert media.source == "none"
        assert media.media_url is None
        assert media.degraded is True


def test_validated_video_resolves_poster_and_fallback_urls():
    with SessionLocal() as db:
        question = _question()
        poster = _image()
        fallback = _image()
        db.add_all([question, poster, fallback]); db.flush()
        video = MediaAsset(
            media_type="video", usage_type="exam",
            secure_url=f"https://media.coderoute.example/{uuid4().hex}.mp4",
            mime_type="video/mp4", width=1920, height=1080, duration_seconds=12,
            file_size_bytes=6_000_000, checksum_sha256=uuid4().hex + uuid4().hex,
            poster_media_id=poster.id, fallback_media_id=fallback.id, theme="INTERSECTIONS",
            country_code="GN", source_type="original", source_reference="CAPTATION-VIDEO-001",
            copyright_owner="CodeRoute Guinée", quality_status="validated", regulatory_status="validated",
            regulatory_authority_reference="DNTT-MEDIA-VIDEO-001",
        )
        db.add(video); db.flush()
        db.add(QuestionMedia(question_id=question.id, media_id=video.id, role="primary")); db.commit()
        media = resolve_exam_media(db, question)
        assert media.source == "normalized"
        assert media.media_type == "video"
        assert media.media_url == video.secure_url
        assert media.poster_url == poster.secure_url
        assert media.fallback_url == fallback.secure_url
        assert media.fallback_media_type == "image"


def test_batch_resolver_preserves_requested_order_and_marks_unknown_question():
    with SessionLocal() as db:
        first = _question(legacy_url="first")
        second = _question(legacy_url="second")
        db.add_all([first, second]); db.commit()
        result = resolve_exam_media_batch(db, [second.id, "missing-id", first.id, second.id])
        assert [item.question_id for item in result] == [second.id, "missing-id", first.id]
        assert result[0].media_url == "second"
        assert result[1].source == "none"
        assert result[1].fallback_reason == "question_missing"
        assert result[2].media_url == "first"

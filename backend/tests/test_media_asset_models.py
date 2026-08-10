from __future__ import annotations

from app.models_media import (
    MEDIA_QUALITY_STATUSES,
    MEDIA_REGULATORY_STATUSES,
    MEDIA_SOURCE_TYPES,
    MEDIA_TYPES,
    MEDIA_USAGE_TYPES,
    QUESTION_MEDIA_ROLES,
    MediaAsset,
    QuestionMedia,
)


def test_media_taxonomies_are_explicit_and_fail_closed() -> None:
    assert set(MEDIA_TYPES) == {"image", "video", "audio"}
    assert set(MEDIA_USAGE_TYPES) == {"exam", "course", "explanation", "thumbnail"}
    assert "legacy" in MEDIA_SOURCE_TYPES
    assert set(MEDIA_QUALITY_STATUSES) == {"draft", "review_required", "validated", "rejected"}
    assert set(MEDIA_REGULATORY_STATUSES) == {"not_reviewed", "under_review", "validated", "rejected"}
    assert set(QUESTION_MEDIA_ROLES) == {"primary", "poster", "fallback", "explanation"}


def test_media_asset_contains_provenance_integrity_and_regulatory_fields() -> None:
    columns = set(MediaAsset.__table__.columns.keys())
    assert {
        "checksum_sha256",
        "source_type",
        "source_reference",
        "license_type",
        "license_reference",
        "license_expiration_date",
        "copyright_owner",
        "quality_status",
        "regulatory_status",
        "regulatory_authority_reference",
        "validated_by",
        "validated_at",
    }.issubset(columns)


def test_media_asset_contains_delivery_and_fallback_metadata() -> None:
    columns = set(MediaAsset.__table__.columns.keys())
    assert {
        "storage_provider",
        "storage_key",
        "public_url",
        "secure_url",
        "mime_type",
        "width",
        "height",
        "duration_seconds",
        "file_size_bytes",
        "poster_media_id",
        "fallback_media_id",
    }.issubset(columns)


def test_question_media_is_many_to_many_role_mapping() -> None:
    columns = set(QuestionMedia.__table__.columns.keys())
    assert {"question_id", "media_id", "role", "display_order"}.issubset(columns)

    foreign_targets = {
        fk.target_fullname
        for column in QuestionMedia.__table__.columns
        for fk in column.foreign_keys
    }
    assert "questions.id" in foreign_targets
    assert "media_assets.id" in foreign_targets


def test_media_asset_defaults_do_not_claim_validation() -> None:
    asset = MediaAsset(media_type="image", usage_type="exam")
    assert asset.quality_status is None or asset.quality_status == "draft"
    assert asset.regulatory_status is None or asset.regulatory_status == "not_reviewed"
    assert asset.validated_at is None
    assert asset.regulatory_authority_reference is None

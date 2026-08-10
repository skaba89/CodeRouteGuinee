"""Normalized media models for premium exam/course assets.

Phase 2 is intentionally additive. The legacy Question.media_type/media_url/
media_alt fields remain the production fallback until the later migration and
API phases have proven full compatibility.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


MEDIA_TYPES = ("image", "video", "audio")
MEDIA_USAGE_TYPES = ("exam", "course", "explanation", "thumbnail")
MEDIA_SOURCE_TYPES = ("original", "licensed", "partner", "public_domain", "internal", "generated", "legacy")
MEDIA_QUALITY_STATUSES = ("draft", "review_required", "validated", "rejected")
MEDIA_REGULATORY_STATUSES = ("not_reviewed", "under_review", "validated", "rejected")
QUESTION_MEDIA_ROLES = ("primary", "poster", "fallback", "explanation")


def new_media_id() -> str:
    return str(uuid.uuid4())


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MediaAsset(Base):
    """One immutable-by-identity media resource plus its validation metadata.

    The actual binary may live on Cloudinary, S3/R2, MinIO or another provider.
    This table stores only delivery/storage references and privacy-safe metadata;
    storage credentials never belong here.
    """

    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("media_type IN ('image','video','audio')", name="ck_media_assets_media_type"),
        CheckConstraint(
            "usage_type IN ('exam','course','explanation','thumbnail')",
            name="ck_media_assets_usage_type",
        ),
        CheckConstraint(
            "source_type IN ('original','licensed','partner','public_domain','internal','generated','legacy')",
            name="ck_media_assets_source_type",
        ),
        CheckConstraint(
            "quality_status IN ('draft','review_required','validated','rejected')",
            name="ck_media_assets_quality_status",
        ),
        CheckConstraint(
            "regulatory_status IN ('not_reviewed','under_review','validated','rejected')",
            name="ck_media_assets_regulatory_status",
        ),
        CheckConstraint("width IS NULL OR width > 0", name="ck_media_assets_width_positive"),
        CheckConstraint("height IS NULL OR height > 0", name="ck_media_assets_height_positive"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="ck_media_assets_duration_nonnegative"),
        CheckConstraint("file_size_bytes IS NULL OR file_size_bytes >= 0", name="ck_media_assets_size_nonnegative"),
        UniqueConstraint("uuid", name="uq_media_assets_uuid"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_media_id)
    # Separate stable UUID is kept because external GED/storage references may
    # use it while the internal PK can remain implementation-specific later.
    uuid: Mapped[str] = mapped_column(String(36), default=new_media_id, nullable=False, index=True)

    media_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    usage_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    storage_provider: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    secure_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    poster_media_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    fallback_media_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )

    theme: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    subtheme: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), default="GN", nullable=False, index=True)
    regulatory_scope: Mapped[str | None] = mapped_column(String(120), nullable=True)

    source_type: Mapped[str] = mapped_column(String(24), default="internal", nullable=False, index=True)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    license_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    copyright_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)

    quality_status: Mapped[str] = mapped_column(
        String(24), default="draft", nullable=False, index=True
    )
    regulatory_status: Mapped[str] = mapped_column(
        String(24), default="not_reviewed", nullable=False, index=True
    )
    regulatory_authority_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    validated_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now_naive, onupdate=_utc_now_naive, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class QuestionMedia(Base):
    """Associates one question with one media asset in a semantic role."""

    __tablename__ = "question_media"
    __table_args__ = (
        CheckConstraint(
            "role IN ('primary','poster','fallback','explanation')",
            name="ck_question_media_role",
        ),
        CheckConstraint("display_order >= 0", name="ck_question_media_display_order_nonnegative"),
        UniqueConstraint("question_id", "media_id", "role", name="uq_question_media_question_asset_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_media_id)
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), default="primary", nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now_naive, nullable=False)

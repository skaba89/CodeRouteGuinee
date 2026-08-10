from __future__ import annotations

import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MediaType = Literal["image", "video", "audio"]
MediaUsageType = Literal["exam", "course", "explanation", "thumbnail"]
MediaSourceType = Literal[
    "original", "licensed", "partner", "public_domain", "internal", "generated", "legacy"
]
MediaQualityStatus = Literal["draft", "review_required", "validated", "rejected"]
MediaRegulatoryStatus = Literal["not_reviewed", "under_review", "validated", "rejected"]
QuestionMediaRole = Literal["primary", "poster", "fallback", "explanation"]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
_OPTIONAL_TEXT_FIELDS = (
    "storage_provider",
    "storage_key",
    "public_url",
    "secure_url",
    "mime_type",
    "poster_media_id",
    "fallback_media_id",
    "theme",
    "subtheme",
    "regulatory_scope",
    "source_reference",
    "license_type",
    "license_reference",
    "copyright_owner",
)


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class MediaAssetCreate(BaseModel):
    media_type: MediaType
    usage_type: MediaUsageType = "exam"
    storage_provider: str | None = Field(default=None, max_length=40)
    storage_key: str | None = Field(default=None, max_length=1024)
    public_url: str | None = Field(default=None, max_length=2048)
    secure_url: str | None = Field(default=None, max_length=2048)
    mime_type: str | None = Field(default=None, max_length=100)
    width: int | None = Field(default=None, ge=1, le=100_000)
    height: int | None = Field(default=None, ge=1, le=100_000)
    duration_seconds: float | None = Field(default=None, ge=0, le=86_400)
    file_size_bytes: int | None = Field(default=None, ge=0, le=20 * 1024 * 1024 * 1024)
    checksum_sha256: str | None = Field(default=None, max_length=64)
    poster_media_id: str | None = Field(default=None, max_length=36)
    fallback_media_id: str | None = Field(default=None, max_length=36)
    theme: str | None = Field(default=None, max_length=80)
    subtheme: str | None = Field(default=None, max_length=120)
    country_code: str = Field(default="GN", min_length=2, max_length=2)
    regulatory_scope: str | None = Field(default=None, max_length=120)
    source_type: MediaSourceType = "internal"
    source_reference: str | None = Field(default=None, max_length=1000)
    license_type: str | None = Field(default=None, max_length=80)
    license_reference: str | None = Field(default=None, max_length=1000)
    license_expiration_date: date | None = None
    copyright_owner: str | None = Field(default=None, max_length=255)

    @field_validator(*_OPTIONAL_TEXT_FIELDS, mode="before")
    @classmethod
    def strip_optional_text(cls, value):
        return _strip(value) if isinstance(value, str) or value is None else value

    @field_validator("checksum_sha256")
    @classmethod
    def validate_checksum(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not _SHA256_RE.fullmatch(normalized):
            raise ValueError("checksum_sha256 doit contenir exactement 64 caractères hexadécimaux")
        return normalized

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not _COUNTRY_RE.fullmatch(normalized):
            raise ValueError("country_code doit être un code ISO alpha-2")
        return normalized


class MediaAssetUpdate(BaseModel):
    media_type: MediaType | None = None
    usage_type: MediaUsageType | None = None
    storage_provider: str | None = Field(default=None, max_length=40)
    storage_key: str | None = Field(default=None, max_length=1024)
    public_url: str | None = Field(default=None, max_length=2048)
    secure_url: str | None = Field(default=None, max_length=2048)
    mime_type: str | None = Field(default=None, max_length=100)
    width: int | None = Field(default=None, ge=1, le=100_000)
    height: int | None = Field(default=None, ge=1, le=100_000)
    duration_seconds: float | None = Field(default=None, ge=0, le=86_400)
    file_size_bytes: int | None = Field(default=None, ge=0, le=20 * 1024 * 1024 * 1024)
    checksum_sha256: str | None = Field(default=None, max_length=64)
    poster_media_id: str | None = Field(default=None, max_length=36)
    fallback_media_id: str | None = Field(default=None, max_length=36)
    theme: str | None = Field(default=None, max_length=80)
    subtheme: str | None = Field(default=None, max_length=120)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    regulatory_scope: str | None = Field(default=None, max_length=120)
    source_type: MediaSourceType | None = None
    source_reference: str | None = Field(default=None, max_length=1000)
    license_type: str | None = Field(default=None, max_length=80)
    license_reference: str | None = Field(default=None, max_length=1000)
    license_expiration_date: date | None = None
    copyright_owner: str | None = Field(default=None, max_length=255)

    @field_validator(*_OPTIONAL_TEXT_FIELDS, mode="before")
    @classmethod
    def strip_optional_text(cls, value):
        return _strip(value) if isinstance(value, str) or value is None else value

    @field_validator("checksum_sha256")
    @classmethod
    def validate_checksum(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not _SHA256_RE.fullmatch(normalized):
            raise ValueError("checksum_sha256 doit contenir exactement 64 caractères hexadécimaux")
        return normalized

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not _COUNTRY_RE.fullmatch(normalized):
            raise ValueError("country_code doit être un code ISO alpha-2")
        return normalized


class MediaAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    uuid: str
    media_type: MediaType
    usage_type: MediaUsageType
    storage_provider: str | None
    storage_key: str | None
    public_url: str | None
    secure_url: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    duration_seconds: float | None
    file_size_bytes: int | None
    checksum_sha256: str | None
    poster_media_id: str | None
    fallback_media_id: str | None
    theme: str | None
    subtheme: str | None
    country_code: str
    regulatory_scope: str | None
    source_type: MediaSourceType
    source_reference: str | None
    license_type: str | None
    license_reference: str | None
    license_expiration_date: date | None
    copyright_owner: str | None
    quality_status: MediaQualityStatus
    regulatory_status: MediaRegulatoryStatus
    regulatory_authority_reference: str | None
    validated_by: str | None
    validated_at: datetime | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class MediaAssetList(BaseModel):
    items: list[MediaAssetRead]
    total: int
    limit: int
    offset: int


class QuestionMediaLinkCreate(BaseModel):
    media_id: str = Field(min_length=1, max_length=36)
    role: QuestionMediaRole = "primary"
    display_order: int = Field(default=0, ge=0, le=10_000)


class QuestionMediaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    question_id: str
    media_id: str
    role: QuestionMediaRole
    display_order: int
    created_at: datetime


class MediaUploadTargetRequest(BaseModel):
    media_type: MediaType
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=100)


class MediaUploadTargetResponse(BaseModel):
    provider: str
    method: Literal["POST", "PUT"]
    upload_url: str
    storage_key: str | None = None
    delivery_url: str | None = None
    expires_in_seconds: int | None = None
    fields: dict[str, str | int] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    policy: dict = Field(default_factory=dict)

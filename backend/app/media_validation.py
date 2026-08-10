"""Server-side validation helpers for MediaAsset metadata.

Phase 3 validates what can be proven from metadata without pretending to perform
human pedagogical/regulatory review. Quality/regulatory approval remains a
separate workflow in Phase 4.
"""
from __future__ import annotations

import re
from typing import Any

from app.media_policy import get_media_upload_policy, validate_media_url

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_STORAGE_KEY_RE = re.compile(r"^[A-Za-z0-9._/=-]{1,1024}$")

VALIDATION_SENSITIVE_FIELDS = {
    "media_type",
    "usage_type",
    "storage_provider",
    "storage_key",
    "public_url",
    "secure_url",
    "mime_type",
    "width",
    "height",
    "duration_seconds",
    "file_size_bytes",
    "checksum_sha256",
    "poster_media_id",
    "fallback_media_id",
    "country_code",
    "regulatory_scope",
    "source_type",
    "source_reference",
    "license_type",
    "license_reference",
    "license_expiration_date",
    "copyright_owner",
}


def validate_asset_metadata(values: dict[str, Any], *, media_type: str) -> dict[str, Any]:
    """Validate and normalize API metadata without upgrading any status."""
    normalized = dict(values)
    media_type = media_type.strip().lower()
    policy = get_media_upload_policy(media_type)

    for key in ("public_url", "secure_url"):
        value = normalized.get(key)
        if value:
            normalized[key] = validate_media_url(str(value), media_type)

    mime = normalized.get("mime_type")
    if mime:
        mime = str(mime).strip().lower()
        allowed = {str(item).lower() for item in policy.get("accepted_mime_types", [])}
        if mime not in allowed:
            raise ValueError(f"MIME {mime!r} interdit pour un média {media_type}")
        normalized["mime_type"] = mime

    size = normalized.get("file_size_bytes")
    max_bytes = policy.get("max_bytes")
    if size is not None and max_bytes is not None and int(size) > int(max_bytes):
        raise ValueError(f"Fichier trop volumineux pour {media_type} (max {int(max_bytes)} octets)")

    duration = normalized.get("duration_seconds")
    max_duration = policy.get("max_duration_seconds")
    if duration is not None and max_duration is not None and float(duration) > float(max_duration):
        raise ValueError(f"Durée trop longue pour {media_type} (max {max_duration} s)")

    checksum = normalized.get("checksum_sha256")
    if checksum:
        checksum = str(checksum).strip().lower()
        if not _SHA256_RE.fullmatch(checksum):
            raise ValueError("checksum_sha256 invalide")
        normalized["checksum_sha256"] = checksum

    storage_key = normalized.get("storage_key")
    if storage_key:
        candidate = str(storage_key).strip().lstrip("/")
        if ".." in candidate.split("/") or not _SAFE_STORAGE_KEY_RE.fullmatch(candidate):
            raise ValueError("storage_key invalide")
        normalized["storage_key"] = candidate

    provider = normalized.get("storage_provider")
    if provider:
        normalized["storage_provider"] = str(provider).strip().lower()

    country = normalized.get("country_code")
    if country:
        normalized["country_code"] = str(country).strip().upper()

    return normalized


def validation_sensitive_changes(before: object, changes: dict[str, Any]) -> set[str]:
    changed: set[str] = set()
    for field in VALIDATION_SENSITIVE_FIELDS.intersection(changes):
        if getattr(before, field, None) != changes[field]:
            changed.add(field)
    return changed

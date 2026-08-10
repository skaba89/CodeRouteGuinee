"""Provider-neutral upload targets for the CodeRoute media factory.

The API returns short-lived upload material only. Long-lived storage secrets are
read server-side from environment variables and are never returned to clients.
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.cloudinary_service import build_upload_signature, is_configured as cloudinary_is_configured
from app.media_policy import get_media_upload_policy

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_PROVIDER_ALIASES = {
    "aws": "s3",
    "aws_s3": "s3",
    "s3": "s3",
    "r2": "r2",
    "cloudflare_r2": "r2",
    "minio": "minio",
    "cloudinary": "cloudinary",
}


class MediaStorageError(RuntimeError):
    """Storage provider is unavailable or incorrectly configured."""


class MediaStorageValidationError(ValueError):
    """The requested provider/upload metadata is invalid client input."""


@dataclass(frozen=True)
class UploadTarget:
    provider: str
    method: str
    upload_url: str
    storage_key: str | None
    expires_in_seconds: int | None
    fields: dict[str, str | int]
    headers: dict[str, str]
    policy: dict

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "method": self.method,
            "upload_url": self.upload_url,
            "storage_key": self.storage_key,
            "expires_in_seconds": self.expires_in_seconds,
            "fields": self.fields,
            "headers": self.headers,
            "policy": self.policy,
        }


class MediaStorageProvider(Protocol):
    name: str

    def build_upload_target(self, *, media_type: str, filename: str, content_type: str) -> UploadTarget: ...


def _safe_filename(filename: str) -> str:
    candidate = Path(filename or "upload").name.strip()
    candidate = _SAFE_FILENAME_RE.sub("-", candidate).strip(".-")
    if not candidate:
        candidate = "upload"
    return candidate[:120]


def _validate_content_type(media_type: str, content_type: str) -> dict:
    try:
        policy = get_media_upload_policy(media_type)
    except ValueError as exc:
        raise MediaStorageValidationError(str(exc)) from exc
    normalized = (content_type or "").strip().lower()
    allowed = {str(value).lower() for value in policy.get("accepted_mime_types", [])}
    if normalized not in allowed:
        raise MediaStorageValidationError(
            f"MIME {content_type!r} interdit pour {media_type}; types acceptés: {sorted(allowed)}"
        )
    return policy


class CloudinaryMediaStorage:
    name = "cloudinary"

    def build_upload_target(self, *, media_type: str, filename: str, content_type: str) -> UploadTarget:
        del filename
        policy = _validate_content_type(media_type, content_type)
        if not cloudinary_is_configured():
            raise MediaStorageError("Cloudinary n'est pas configuré")
        signed = build_upload_signature(media_type)
        fields = {
            "api_key": str(signed["api_key"]),
            "timestamp": int(signed["timestamp"]),
            "folder": str(signed["folder"]),
            "signature": str(signed["signature"]),
        }
        return UploadTarget(
            provider=self.name,
            method="POST",
            upload_url=str(signed["upload_url"]),
            storage_key=None,
            expires_in_seconds=15 * 60,
            fields=fields,
            headers={},
            policy=policy,
        )


class S3CompatibleMediaStorage:
    def __init__(self, name: str) -> None:
        self.name = name

    def build_upload_target(self, *, media_type: str, filename: str, content_type: str) -> UploadTarget:
        policy = _validate_content_type(media_type, content_type)
        bucket = os.getenv("MEDIA_S3_BUCKET", "").strip()
        if not bucket:
            raise MediaStorageError("MEDIA_S3_BUCKET est obligatoire pour un stockage S3-compatible")

        prefix = os.getenv("MEDIA_S3_PREFIX", "coderoute/media").strip("/")
        safe_name = _safe_filename(filename)
        storage_key = f"{prefix}/{media_type}/{uuid.uuid4()}/{safe_name}"
        expires = 15 * 60

        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - dependency is part of production requirements
            raise MediaStorageError("boto3 est requis pour un stockage S3-compatible") from exc

        endpoint = os.getenv("MEDIA_S3_ENDPOINT_URL", "").strip() or None
        region = os.getenv("MEDIA_S3_REGION", "").strip() or None
        access_key = os.getenv("MEDIA_S3_ACCESS_KEY_ID", "").strip() or None
        secret_key = os.getenv("MEDIA_S3_SECRET_ACCESS_KEY", "").strip() or None
        session_token = os.getenv("MEDIA_S3_SESSION_TOKEN", "").strip() or None

        client_kwargs: dict = {}
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint
        if region:
            client_kwargs["region_name"] = region
        if access_key:
            client_kwargs["aws_access_key_id"] = access_key
        if secret_key:
            client_kwargs["aws_secret_access_key"] = secret_key
        if session_token:
            client_kwargs["aws_session_token"] = session_token

        try:
            client = boto3.client("s3", **client_kwargs)
            upload_url = client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": storage_key, "ContentType": content_type},
                ExpiresIn=expires,
            )
        except Exception as exc:  # noqa: BLE001 - provider SDK failures are translated to a safe operational error
            raise MediaStorageError(f"Impossible de générer la cible d'upload {self.name}") from exc

        return UploadTarget(
            provider=self.name,
            method="PUT",
            upload_url=upload_url,
            storage_key=storage_key,
            expires_in_seconds=expires,
            fields={},
            headers={"Content-Type": content_type},
            policy=policy,
        )


def get_media_storage_provider(name: str | None = None) -> MediaStorageProvider:
    requested = (name or os.getenv("MEDIA_STORAGE_PROVIDER", "cloudinary")).strip().lower()
    normalized = _PROVIDER_ALIASES.get(requested)
    if normalized is None:
        raise MediaStorageValidationError(
            "MEDIA_STORAGE_PROVIDER doit être cloudinary, s3/aws_s3, r2/cloudflare_r2 ou minio"
        )
    if normalized == "cloudinary":
        return CloudinaryMediaStorage()
    return S3CompatibleMediaStorage(normalized)

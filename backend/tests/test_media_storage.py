from __future__ import annotations

import pytest

from app import media_storage
from app.media_storage import (
    CloudinaryMediaStorage,
    MediaStorageError,
    MediaStorageValidationError,
    S3CompatibleMediaStorage,
    get_media_storage_provider,
)


def test_unknown_storage_provider_is_validation_error():
    with pytest.raises(MediaStorageValidationError, match="MEDIA_STORAGE_PROVIDER"):
        get_media_storage_provider("ftp")


def test_provider_aliases_are_normalized():
    assert get_media_storage_provider("cloudinary").name == "cloudinary"
    assert get_media_storage_provider("aws_s3").name == "s3"
    assert get_media_storage_provider("cloudflare_r2").name == "r2"
    assert get_media_storage_provider("minio").name == "minio"


def test_invalid_mime_is_client_validation_error():
    provider = S3CompatibleMediaStorage("s3")
    with pytest.raises(MediaStorageValidationError, match="MIME"):
        provider.build_upload_target(
            media_type="image",
            filename="danger.svg",
            content_type="image/svg+xml",
        )


def test_s3_compatible_target_uses_presigned_put_without_exposing_credentials(monkeypatch):
    captured = {}

    class FakeS3:
        def generate_presigned_url(self, operation, Params, ExpiresIn):
            captured.update({"operation": operation, "Params": Params, "ExpiresIn": ExpiresIn})
            return "https://objects.example.test/presigned-upload?signature=short-lived"

    import boto3

    monkeypatch.setenv("MEDIA_S3_BUCKET", "coderoute-media")
    monkeypatch.setenv("MEDIA_S3_PREFIX", "national/media")
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "https://media.coderoute.example")
    monkeypatch.setenv("MEDIA_S3_ACCESS_KEY_ID", "sensitive-access-key")
    monkeypatch.setenv("MEDIA_S3_SECRET_ACCESS_KEY", "sensitive-secret-key")
    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: FakeS3())

    target = S3CompatibleMediaStorage("r2").build_upload_target(
        media_type="video",
        filename="../Intersection premium.mp4",
        content_type="video/mp4",
    )

    payload = target.as_dict()
    serialized = repr(payload)
    assert target.provider == "r2"
    assert target.method == "PUT"
    assert target.upload_url.startswith("https://objects.example.test/presigned-upload?")
    assert target.storage_key is not None
    assert target.storage_key.startswith("national/media/video/")
    assert ".." not in target.storage_key
    assert "Intersection-premium.mp4" in target.storage_key
    assert target.delivery_url == f"https://media.coderoute.example/{target.storage_key}"
    assert "signature=" not in target.delivery_url
    assert target.headers == {"Content-Type": "video/mp4"}
    assert "sensitive-access-key" not in serialized
    assert "sensitive-secret-key" not in serialized
    assert captured["Params"]["Bucket"] == "coderoute-media"
    assert captured["Params"]["ContentType"] == "video/mp4"
    assert captured["ExpiresIn"] == 900


def test_s3_requires_bucket(monkeypatch):
    monkeypatch.delenv("MEDIA_S3_BUCKET", raising=False)
    with pytest.raises(MediaStorageError, match="MEDIA_S3_BUCKET"):
        S3CompatibleMediaStorage("s3").build_upload_target(
            media_type="image",
            filename="q1.webp",
            content_type="image/webp",
        )


def test_s3_requires_durable_https_delivery_base(monkeypatch):
    monkeypatch.setenv("MEDIA_S3_BUCKET", "coderoute-media")
    monkeypatch.delenv("MEDIA_PUBLIC_BASE_URL", raising=False)
    with pytest.raises(MediaStorageError, match="MEDIA_PUBLIC_BASE_URL"):
        S3CompatibleMediaStorage("s3").build_upload_target(
            media_type="image",
            filename="q1.webp",
            content_type="image/webp",
        )

    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "http://media.internal")
    with pytest.raises(MediaStorageError, match="HTTPS"):
        S3CompatibleMediaStorage("s3").build_upload_target(
            media_type="image",
            filename="q1.webp",
            content_type="image/webp",
        )


def test_cloudinary_target_supports_audio_via_provider_video(monkeypatch):
    monkeypatch.setattr(media_storage, "cloudinary_is_configured", lambda: True)
    monkeypatch.setattr(
        media_storage,
        "build_upload_signature",
        lambda media_type: {
            "upload_url": "https://api.cloudinary.com/v1_1/demo/video/upload",
            "api_key": "public-api-key",
            "timestamp": 123,
            "folder": "coderoute/questions",
            "signature": "signature-value",
            "resource_type": media_type,
            "provider_resource_type": "video",
        },
    )

    target = CloudinaryMediaStorage().build_upload_target(
        media_type="audio",
        filename="q1.mp3",
        content_type="audio/mpeg",
    )
    assert target.provider == "cloudinary"
    assert target.method == "POST"
    assert target.delivery_url is None
    assert target.upload_url.endswith("/video/upload")
    assert target.fields["api_key"] == "public-api-key"
    assert target.policy["resource_type"] == "audio"

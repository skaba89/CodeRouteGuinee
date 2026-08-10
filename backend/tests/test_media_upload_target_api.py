from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from conftest import get_auth_headers


def test_unknown_upload_provider_is_422():
    with TestClient(app) as client:
        headers = get_auth_headers(client, "admin")
        response = client.post(
            "/api/v1/media-library/upload-target?provider=ftp",
            headers=headers,
            json={
                "media_type": "image",
                "filename": "intersection.webp",
                "content_type": "image/webp",
            },
        )
    assert response.status_code == 422
    assert "MEDIA_STORAGE_PROVIDER" in str(response.json())


def test_unconfigured_s3_upload_provider_is_503(monkeypatch):
    monkeypatch.delenv("MEDIA_S3_BUCKET", raising=False)
    with TestClient(app) as client:
        headers = get_auth_headers(client, "admin")
        response = client.post(
            "/api/v1/media-library/upload-target?provider=s3",
            headers=headers,
            json={
                "media_type": "video",
                "filename": "intersection.mp4",
                "content_type": "video/mp4",
            },
        )
    assert response.status_code == 503
    assert "MEDIA_S3_BUCKET" in str(response.json())


def test_invalid_upload_mime_is_422_before_provider_configuration():
    with TestClient(app) as client:
        headers = get_auth_headers(client, "admin")
        response = client.post(
            "/api/v1/media-library/upload-target?provider=s3",
            headers=headers,
            json={
                "media_type": "image",
                "filename": "unsafe.svg",
                "content_type": "image/svg+xml",
            },
        )
    assert response.status_code == 422
    assert "MIME" in str(response.json())

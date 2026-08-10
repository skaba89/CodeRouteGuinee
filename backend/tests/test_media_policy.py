"""Tests de sécurité — politique des médias d'examen."""
from __future__ import annotations

import pytest

from app.media_policy import get_media_upload_policy, validate_media_url


def test_public_https_image_url_is_allowed():
    url = "https://cdn.coderoute.example/media/intersection-001.webp"
    assert validate_media_url(url, "image") == url


def test_public_https_audio_url_is_allowed():
    url = "https://cdn.coderoute.example/audio/q001-pular.mp3"
    assert validate_media_url(url, "audio") == url


def test_public_http_media_is_rejected():
    with pytest.raises(ValueError, match="HTTPS"):
        validate_media_url("http://cdn.coderoute.example/media/q1.jpg", "image")


def test_private_ip_media_is_rejected():
    with pytest.raises(ValueError, match="privée|publique"):
        validate_media_url("https://10.10.0.5/question.jpg", "image")


def test_internal_hostname_is_rejected():
    with pytest.raises(ValueError, match="interne"):
        validate_media_url("https://media.internal/question.jpg", "image")


def test_embedded_credentials_are_rejected():
    with pytest.raises(ValueError, match="identifiants"):
        validate_media_url("https://admin:secret@cdn.coderoute.example/question.jpg", "image")


def test_malformed_port_is_rejected_as_validation_error():
    with pytest.raises(ValueError, match="port"):
        validate_media_url("https://cdn.coderoute.example:abc/question.jpg", "image")


def test_cloudinary_upload_api_cannot_be_persisted_as_delivery_url():
    with pytest.raises(ValueError, match="upload Cloudinary"):
        validate_media_url("https://api.cloudinary.com/v1_1/demo/image/upload", "image")


def test_cloudinary_resource_type_must_match_declared_type():
    with pytest.raises(ValueError, match="type déclaré"):
        validate_media_url(
            "https://res.cloudinary.com/demo/video/upload/v1/questions/clip.mp4",
            "image",
        )


def test_cloudinary_audio_is_delivered_through_video_resource_type():
    url = "https://res.cloudinary.com/demo/video/upload/v1/audio/q1.mp3"
    assert validate_media_url(url, "audio") == url
    with pytest.raises(ValueError, match="type déclaré"):
        validate_media_url(
            "https://res.cloudinary.com/demo/image/upload/v1/audio/q1.mp3",
            "audio",
        )


def test_unknown_media_type_is_rejected():
    with pytest.raises(ValueError, match="type de média"):
        validate_media_url("https://cdn.coderoute.example/file.pdf", "document")


def test_image_upload_policy_is_mobile_network_aware():
    policy = get_media_upload_policy("image")
    assert policy["max_bytes"] == 10 * 1024 * 1024
    assert "image/webp" in policy["accepted_mime_types"]
    assert "avif" in policy["delivery_formats"]
    assert policy["recommended_min_width"] >= 1280


def test_video_upload_policy_limits_duration_and_requires_adaptive_delivery():
    policy = get_media_upload_policy("video")
    assert policy["max_duration_seconds"] == 30
    assert policy["adaptive_streaming"] is True
    assert policy["poster_required"] is True
    assert "720p" in policy["delivery_profiles"]


def test_audio_upload_policy_is_bounded_and_mobile_friendly():
    policy = get_media_upload_policy("audio")
    assert policy["max_bytes"] == 15 * 1024 * 1024
    assert policy["max_duration_seconds"] == 600
    assert "audio/mpeg" in policy["accepted_mime_types"]
    assert "mp3" in policy["delivery_formats"]

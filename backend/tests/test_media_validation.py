from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.media_validation import validate_asset_metadata, validation_sensitive_changes


def test_image_metadata_is_normalized_without_granting_validation():
    values = validate_asset_metadata(
        {
            "public_url": "https://cdn.coderoute.example/q1.webp",
            "mime_type": " IMAGE/WEBP ",
            "file_size_bytes": 1_000_000,
            "checksum_sha256": "A" * 64,
            "storage_provider": " Cloudinary ",
            "storage_key": "/coderoute/media/q1.webp",
            "country_code": "gn",
        },
        media_type="image",
    )
    assert values["mime_type"] == "image/webp"
    assert values["checksum_sha256"] == "a" * 64
    assert values["storage_provider"] == "cloudinary"
    assert values["storage_key"] == "coderoute/media/q1.webp"
    assert values["country_code"] == "GN"
    assert "quality_status" not in values
    assert "regulatory_status" not in values


def test_svg_and_oversized_image_are_rejected():
    with pytest.raises(ValueError, match="MIME"):
        validate_asset_metadata({"mime_type": "image/svg+xml"}, media_type="image")
    with pytest.raises(ValueError, match="volumineux"):
        validate_asset_metadata({"file_size_bytes": 11 * 1024 * 1024}, media_type="image")


def test_video_over_policy_duration_is_rejected():
    with pytest.raises(ValueError, match="Durée"):
        validate_asset_metadata({"duration_seconds": 31}, media_type="video")


def test_invalid_checksum_and_storage_traversal_are_rejected():
    with pytest.raises(ValueError, match="checksum"):
        validate_asset_metadata({"checksum_sha256": "abc"}, media_type="image")
    with pytest.raises(ValueError, match="storage_key"):
        validate_asset_metadata({"storage_key": "coderoute/../secret"}, media_type="image")


def test_validation_sensitive_changes_detect_binary_and_rights_changes():
    asset = SimpleNamespace(
        checksum_sha256="a" * 64,
        copyright_owner="Owner A",
        theme="priorites",
    )
    changed = validation_sensitive_changes(
        asset,
        {
            "checksum_sha256": "b" * 64,
            "copyright_owner": "Owner B",
            "theme": "priorites",
        },
    )
    assert changed == {"checksum_sha256", "copyright_owner"}

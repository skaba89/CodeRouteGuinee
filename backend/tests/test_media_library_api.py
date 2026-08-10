from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from tests.conftest import get_auth_headers


@pytest.fixture(autouse=True)
def clean_media_library_rows():
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


def _asset_payload(*, checksum: str = "a" * 64, source_type: str = "licensed") -> dict:
    return {
        "media_type": "image",
        "usage_type": "exam",
        "storage_provider": "cloudinary",
        "storage_key": f"coderoute/questions/{uuid4().hex}.webp",
        "secure_url": f"https://cdn.coderoute.example/{uuid4().hex}.webp",
        "mime_type": "image/webp",
        "width": 1920,
        "height": 1080,
        "file_size_bytes": 800_000,
        "checksum_sha256": checksum,
        "theme": "priorites",
        "country_code": "GN",
        "source_type": source_type,
        "source_reference": "LICENCE-2026-001",
        "license_type": "commercial",
        "license_reference": "GED-LICENCE-001",
        "copyright_owner": "CodeRoute Media Partner",
    }


def _create_question() -> str:
    with SessionLocal() as db:
        question = Question(
            category="priorites",
            text=f"Question média {uuid4().hex}",
            options=["A", "B", "C"],
            correct_answer="A",
            explanation="Explication",
            is_active=True,
            validation_status="draft",
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question.id


def test_media_library_requires_admin_authentication():
    with TestClient(app) as client:
        assert client.get("/api/v1/media-library/assets").status_code == 401
        candidate = get_auth_headers(client, "candidate")
        assert client.get("/api/v1/media-library/assets", headers=candidate).status_code == 403


def test_create_list_get_asset_starts_fail_closed():
    with TestClient(app) as client:
        headers = get_auth_headers(client, "admin")
        response = client.post("/api/v1/media-library/assets", headers=headers, json=_asset_payload())
        assert response.status_code == 201, response.text
        asset = response.json()
        assert asset["quality_status"] == "draft"
        assert asset["regulatory_status"] == "not_reviewed"
        assert asset["checksum_sha256"] == "a" * 64
        assert asset["created_by"]
        assert asset["validated_by"] is None
        assert asset["validated_at"] is None

        listed = client.get(
            "/api/v1/media-library/assets?media_type=image&theme=priorites",
            headers=headers,
        )
        assert listed.status_code == 200
        body = listed.json()
        assert body["total"] >= 1
        assert any(item["id"] == asset["id"] for item in body["items"])

        fetched = client.get(f"/api/v1/media-library/assets/{asset['id']}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["id"] == asset["id"]


def test_duplicate_checksum_is_rejected():
    with TestClient(app) as client:
        headers = get_auth_headers(client, "super_admin")
        first = client.post("/api/v1/media-library/assets", headers=headers, json=_asset_payload())
        assert first.status_code == 201
        second = client.post("/api/v1/media-library/assets", headers=headers, json=_asset_payload())
        assert second.status_code == 409
        assert second.json()["detail"]["media_id"] == first.json()["id"]


def test_invalid_mime_or_unsafe_url_is_rejected_before_persistence():
    with TestClient(app) as client:
        headers = get_auth_headers(client, "admin")
        svg = _asset_payload(checksum="b" * 64)
        svg["mime_type"] = "image/svg+xml"
        response = client.post("/api/v1/media-library/assets", headers=headers, json=svg)
        assert response.status_code == 422

        private = _asset_payload(checksum="c" * 64)
        private["secure_url"] = "https://127.0.0.1/private.webp"
        response = client.post("/api/v1/media-library/assets", headers=headers, json=private)
        assert response.status_code == 422


def test_binary_change_invalidates_previous_quality_and_regulatory_validation():
    with TestClient(app) as client:
        headers = get_auth_headers(client, "super_admin")
        created = client.post("/api/v1/media-library/assets", headers=headers, json=_asset_payload()).json()

        with SessionLocal() as db:
            asset = db.get(MediaAsset, created["id"])
            assert asset is not None
            asset.quality_status = "validated"
            asset.regulatory_status = "validated"
            asset.validated_by = created["created_by"]
            asset.validated_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()

        response = client.patch(
            f"/api/v1/media-library/assets/{created['id']}",
            headers=headers,
            json={
                "checksum_sha256": "d" * 64,
                "secure_url": "https://cdn.coderoute.example/replacement.webp",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["quality_status"] == "review_required"
        assert body["regulatory_status"] == "under_review"
        assert body["validated_by"] is None
        assert body["validated_at"] is None


def test_question_media_link_is_additive_and_does_not_touch_legacy_fields():
    question_id = _create_question()
    with TestClient(app) as client:
        headers = get_auth_headers(client, "admin")
        asset = client.post("/api/v1/media-library/assets", headers=headers, json=_asset_payload()).json()

        linked = client.post(
            f"/api/v1/media-library/questions/{question_id}/links",
            headers=headers,
            json={"media_id": asset["id"], "role": "primary", "display_order": 0},
        )
        assert linked.status_code == 201, linked.text
        link = linked.json()
        assert link["question_id"] == question_id
        assert link["media_id"] == asset["id"]
        assert link["role"] == "primary"

        duplicate_role_asset = _asset_payload(checksum="e" * 64)
        second = client.post("/api/v1/media-library/assets", headers=headers, json=duplicate_role_asset).json()
        conflict = client.post(
            f"/api/v1/media-library/questions/{question_id}/links",
            headers=headers,
            json={"media_id": second["id"], "role": "primary"},
        )
        assert conflict.status_code == 409

        with SessionLocal() as db:
            question = db.get(Question, question_id)
            assert question is not None
            assert question.media_type is None
            assert question.media_url is None
            assert question.media_alt is None

        listed = client.get(f"/api/v1/media-library/questions/{question_id}", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        removed = client.delete(
            f"/api/v1/media-library/questions/{question_id}/links/{link['id']}",
            headers=headers,
        )
        assert removed.status_code == 204


def test_archived_asset_is_hidden_by_default_and_cannot_be_linked():
    question_id = _create_question()
    with TestClient(app) as client:
        headers = get_auth_headers(client, "admin")
        asset = client.post("/api/v1/media-library/assets", headers=headers, json=_asset_payload()).json()
        archived = client.post(f"/api/v1/media-library/assets/{asset['id']}/archive", headers=headers)
        assert archived.status_code == 200
        assert archived.json()["archived_at"] is not None

        default_list = client.get("/api/v1/media-library/assets", headers=headers).json()
        assert all(item["id"] != asset["id"] for item in default_list["items"])
        with_archived = client.get(
            "/api/v1/media-library/assets?include_archived=true",
            headers=headers,
        ).json()
        assert any(item["id"] == asset["id"] for item in with_archived["items"])

        link = client.post(
            f"/api/v1/media-library/questions/{question_id}/links",
            headers=headers,
            json={"media_id": asset["id"], "role": "primary"},
        )
        assert link.status_code == 409

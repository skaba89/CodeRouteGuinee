from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal, init_db
from app.main import app
from app.media_quality import evaluate_media_asset, evaluate_question_media_gate
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from conftest import get_auth_headers


@pytest.fixture(autouse=True)
def clean_media_quality_rows():
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


def _question(*, status: str = "submitted") -> str:
    with SessionLocal() as db:
        row = Question(
            category="priorites",
            text=f"Question premium {uuid4().hex}",
            options=["A", "B"],
            correct_answer="A",
            explanation="Explication",
            validation_status=status,
            is_active=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def _image_asset(*, created_by: str | None = None, quality: str = "draft", regulatory: str = "not_reviewed") -> MediaAsset:
    return MediaAsset(
        media_type="image",
        usage_type="exam",
        storage_provider="cloudinary",
        storage_key=f"coderoute/questions/{uuid4().hex}.webp",
        secure_url=f"https://cdn.coderoute.example/{uuid4().hex}.webp",
        mime_type="image/webp",
        width=1920,
        height=1080,
        file_size_bytes=800_000,
        checksum_sha256=uuid4().hex + uuid4().hex,
        country_code="GN",
        source_type="licensed",
        source_reference="SOURCE-001",
        license_type="commercial",
        license_reference="GED-LIC-001",
        copyright_owner="CodeRoute Media Partner",
        quality_status=quality,
        regulatory_status=regulatory,
        regulatory_authority_reference="DNTT-MEDIA-001" if regulatory == "validated" else None,
        created_by=created_by,
    )


def test_premium_image_gate_requires_human_quality_and_regulatory_approval():
    with SessionLocal() as db:
        asset = _image_asset()
        db.add(asset)
        db.commit()
        db.refresh(asset)

        initial = evaluate_media_asset(db, asset, require_quality_approval=True, require_regulatory_approval=True)
        assert initial["passed"] is False
        assert "PEDAGOGICAL_QUALITY_APPROVED" in " ".join(initial["blockers"])
        assert "REGULATORY_APPROVED" in " ".join(initial["blockers"])
        assert initial["institutional_validation_inferred"] is False

        asset.quality_status = "validated"
        asset.regulatory_status = "validated"
        asset.regulatory_authority_reference = "DNTT-MEDIA-001"
        db.commit()

        final = evaluate_media_asset(db, asset, require_quality_approval=True, require_regulatory_approval=True)
        assert final["passed"] is True
        assert final["score"] == 100


def test_expired_license_blocks_premium_media():
    with SessionLocal() as db:
        asset = _image_asset(quality="validated", regulatory="validated")
        asset.license_expiration_date = date.today() - timedelta(days=1)
        db.add(asset)
        db.commit()
        result = evaluate_media_asset(db, asset, require_quality_approval=True, require_regulatory_approval=True)
        assert result["passed"] is False
        assert any("RIGHTS_TRACEABLE" in blocker for blocker in result["blockers"])


def test_generated_or_legacy_primary_media_never_passes_official_exam_gate():
    with SessionLocal() as db:
        for source_type in ("generated", "legacy"):
            asset = _image_asset(quality="validated", regulatory="validated")
            asset.source_type = source_type
            db.add(asset)
            db.flush()
            result = evaluate_media_asset(
                db,
                asset,
                require_quality_approval=True,
                require_regulatory_approval=True,
                require_exam_usage=True,
            )
            assert result["passed"] is False
            assert any("SOURCE_TRACEABLE" in blocker for blocker in result["blockers"])
        db.rollback()


def test_exam_video_requires_six_to_twenty_seconds_and_validated_poster_fallback():
    with SessionLocal() as db:
        poster = _image_asset(quality="validated")
        fallback = _image_asset(quality="validated")
        db.add_all([poster, fallback])
        db.flush()
        video = MediaAsset(
            media_type="video",
            usage_type="exam",
            storage_provider="cloudinary",
            storage_key=f"coderoute/questions/{uuid4().hex}.mp4",
            secure_url=f"https://cdn.coderoute.example/{uuid4().hex}.mp4",
            mime_type="video/mp4",
            width=1920,
            height=1080,
            duration_seconds=12,
            file_size_bytes=8_000_000,
            checksum_sha256=uuid4().hex + uuid4().hex,
            poster_media_id=poster.id,
            fallback_media_id=fallback.id,
            country_code="GN",
            source_type="original",
            source_reference="CAPTATION-2026-001",
            copyright_owner="CodeRoute Guinée",
            quality_status="validated",
            regulatory_status="validated",
            regulatory_authority_reference="DNTT-MEDIA-VIDEO-001",
        )
        db.add(video)
        db.commit()
        assert evaluate_media_asset(
            db,
            video,
            require_quality_approval=True,
            require_regulatory_approval=True,
            require_exam_usage=True,
        )["passed"] is True

        video.duration_seconds = 25
        db.commit()
        invalid = evaluate_media_asset(
            db,
            video,
            require_quality_approval=True,
            require_regulatory_approval=True,
            require_exam_usage=True,
        )
        assert invalid["passed"] is False
        assert any("EXAM_VIDEO_DURATION" in blocker for blocker in invalid["blockers"])


def test_legacy_question_without_normalized_primary_remains_compatible():
    question_id = _question(status="submitted")
    with SessionLocal() as db:
        gate = evaluate_question_media_gate(db, question_id, require_regulatory_approval=True)
        assert gate["mode"] == "legacy_compatibility"
        assert gate["passed"] is True
        assert gate["legacy_migration_required"] is True

    with TestClient(app) as client:
        super_headers = get_auth_headers(client, "super_admin")
        response = client.post(f"/api/v1/questions/{question_id}/approve", headers=super_headers)
        assert response.status_code == 200, response.text
        assert response.json()["validation_status"] == "approved"


def test_normalized_question_approval_is_blocked_until_media_is_fully_validated():
    question_id = _question(status="submitted")
    with SessionLocal() as db:
        asset = _image_asset(quality="review_required", regulatory="under_review")
        db.add(asset)
        db.flush()
        db.add(QuestionMedia(question_id=question_id, media_id=asset.id, role="primary", display_order=0))
        db.commit()
        media_id = asset.id

    with TestClient(app) as client:
        super_headers = get_auth_headers(client, "super_admin")
        blocked = client.post(f"/api/v1/questions/{question_id}/approve", headers=super_headers)
        assert blocked.status_code == 409, blocked.text
        detail = blocked.json()["detail"]
        assert detail["code"] == "MEDIA_QUALITY_GATE_BLOCKED"
        assert detail["assessment"]["media_id"] == media_id
        assert detail["assessment"]["mode"] == "normalized"

    with SessionLocal() as db:
        question = db.get(Question, question_id)
        asset = db.get(MediaAsset, media_id)
        assert question is not None and question.validation_status == "submitted"
        assert asset is not None
        asset.quality_status = "validated"
        asset.regulatory_status = "validated"
        asset.regulatory_authority_reference = "DNTT-MEDIA-READY-001"
        asset.validated_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()

    with TestClient(app) as client:
        super_headers = get_auth_headers(client, "super_admin")
        approved = client.post(f"/api/v1/questions/{question_id}/approve", headers=super_headers)
        assert approved.status_code == 200, approved.text
        assert approved.json()["validation_status"] == "approved"


def test_quality_and_regulatory_workflow_enforces_four_eyes():
    with TestClient(app) as client:
        creator_headers = get_auth_headers(client, "admin")
        created = client.post(
            "/api/v1/media-library/assets",
            headers=creator_headers,
            json={
                "media_type": "image",
                "usage_type": "exam",
                "secure_url": "https://cdn.coderoute.example/four-eyes.webp",
                "mime_type": "image/webp",
                "width": 1920,
                "height": 1080,
                "file_size_bytes": 700000,
                "checksum_sha256": "b" * 64,
                "country_code": "GN",
                "source_type": "licensed",
                "source_reference": "SOURCE-FOUR-EYES",
                "license_type": "commercial",
                "license_reference": "GED-LIC-FOUR-EYES",
                "copyright_owner": "Partner",
            },
        )
        assert created.status_code == 201, created.text
        media_id = created.json()["id"]

        submitted = client.post(
            f"/api/v1/media-library/assets/{media_id}/quality/submit",
            headers=creator_headers,
            json={"reason": "Prêt pour revue pédagogique"},
        )
        assert submitted.status_code == 200

        self_approve = client.post(
            f"/api/v1/media-library/assets/{media_id}/quality/approve",
            headers=creator_headers,
            json={"reason": "Auto validation interdite"},
        )
        assert self_approve.status_code == 409
        assert self_approve.json()["detail"]["code"] == "MEDIA_FOUR_EYES_REQUIRED"

        reviewer_headers = get_auth_headers(client, "admin")
        quality = client.post(
            f"/api/v1/media-library/assets/{media_id}/quality/approve",
            headers=reviewer_headers,
            json={"reason": "Qualité et pédagogie conformes"},
        )
        assert quality.status_code == 200, quality.text
        assert quality.json()["quality_status"] == "validated"

        regulatory_submit = client.post(
            f"/api/v1/media-library/assets/{media_id}/regulatory/submit",
            headers=reviewer_headers,
            json={"reason": "Transmission à l'autorité"},
        )
        assert regulatory_submit.status_code == 200
        assert regulatory_submit.json()["regulatory_status"] == "under_review"

        super_headers = get_auth_headers(client, "super_admin")
        regulatory = client.post(
            f"/api/v1/media-library/assets/{media_id}/regulatory/approve",
            headers=super_headers,
            json={
                "authority_reference": "DNTT-MEDIA-2026-0001",
                "reason": "Validation réglementaire formalisée",
            },
        )
        assert regulatory.status_code == 200, regulatory.text
        assert regulatory.json()["regulatory_status"] == "validated"
        assert regulatory.json()["regulatory_authority_reference"] == "DNTT-MEDIA-2026-0001"

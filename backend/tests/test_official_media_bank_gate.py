from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.exam_engine import CATEGORY_DISTRIBUTION
from app.main import app
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.official_exam_attempt_service import create_media_safe_exam_attempt
from app.official_media_readiness import assess_official_question_media, build_official_media_bank_readiness
from app.routers import exams
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _question(db, marker: str, category: str, index: int, *, legacy: bool = True) -> Question:
    question = Question(
        category=category,
        text=f"Situation premium {marker} {category} {index}",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="Explication pédagogique",
        media_type="image" if legacy else None,
        media_url=f"https://legacy.example.test/{marker}/{category}-{index}.webp" if legacy else None,
        media_alt=f"Situation routière {category} {index}" if legacy else None,
        is_active=True,
        validation_status="approved",
        validated_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(question)
    db.flush()
    return question


def _bank(db, marker: str, *, legacy: bool = True) -> list[Question]:
    result: list[Question] = []
    for category, count in CATEGORY_DISTRIBUTION.items():
        for index in range(count):
            result.append(_question(db, marker, category, index, legacy=legacy))
    return result


def _asset(
    db,
    marker: str,
    *,
    valid: bool,
    media_type: str = "image",
    poster_media_id: str | None = None,
    fallback_media_id: str | None = None,
) -> MediaAsset:
    is_video = media_type == "video"
    extension = "mp4" if is_video else "webp"
    asset = MediaAsset(
        media_type=media_type,
        usage_type="exam",
        storage_provider="internal-test",
        storage_key=f"official/{marker}.{extension}",
        secure_url=f"https://cdn.example.test/official/{marker}.{extension}",
        mime_type="video/mp4" if is_video else "image/webp",
        width=1600,
        height=900,
        duration_seconds=10.0 if is_video else None,
        file_size_bytes=900_000 if is_video else 250_000,
        checksum_sha256=("a" * 64),
        poster_media_id=poster_media_id,
        fallback_media_id=fallback_media_id,
        theme="signalisation",
        country_code="GN",
        regulatory_scope="CodeRoute Guinée",
        source_type="internal",
        source_reference=f"GED-MEDIA-{marker}",
        copyright_owner="CodeRoute Guinée",
        quality_status="validated" if valid else "review_required",
        regulatory_status="validated" if valid else "under_review",
        regulatory_authority_reference=f"MEDIA-AUTH-{marker}" if valid else None,
        validated_at=datetime.now(UTC).replace(tzinfo=None) if valid else None,
    )
    db.add(asset)
    db.flush()
    return asset


def _normalized_bank(db, marker: str) -> tuple[list[Question], list[MediaAsset]]:
    questions = _bank(db, marker, legacy=False)
    primaries: list[MediaAsset] = []
    for index, question in enumerate(questions):
        if index % 2 == 1:
            poster = _asset(db, f"{marker}-poster-{index:02d}", valid=True)
            fallback = _asset(db, f"{marker}-fallback-{index:02d}", valid=True)
            primary = _asset(
                db,
                f"{marker}-video-{index:02d}",
                valid=True,
                media_type="video",
                poster_media_id=poster.id,
                fallback_media_id=fallback.id,
            )
        else:
            primary = _asset(db, f"{marker}-image-{index:02d}", valid=True)
        db.add(
            QuestionMedia(
                question_id=question.id,
                media_id=primary.id,
                role="primary",
                display_order=0,
            )
        )
        primaries.append(primary)
    db.flush()
    return questions, primaries


def _isolate_active_question_bank(db) -> None:
    """Hide any bank created by earlier tests without committing the mutation."""
    existing = list(db.scalars(select(Question).where(Question.is_active.is_(True))).all())
    for question in existing:
        question.is_active = False
    db.flush()


def _admin(db, marker: str) -> User:
    user = User(
        email=f"media-admin-{marker}@coderoute.test",
        full_name="Media Admin",
        password_hash=get_password_hash("MediaAdmin123!"),
        role="super_admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _candidate_session(db, marker: str) -> tuple[Candidate, ExamSession]:
    center = Center(
        code=f"MEDIA-{marker}",
        name=f"Centre Media {marker}",
        city="Conakry",
        commune="Kaloum",
        prefecture="Conakry",
        address="Kaloum",
        capacity=35,
        max_sessions_per_week=3,
        status="accredited",
    )
    db.add(center)
    db.flush()
    candidate = Candidate(
        reference=f"GN-CODE-MEDIA-{marker}",
        first_name="Moussa",
        last_name="Barry",
        identity_number=f"ID-MEDIA-{marker}",
        phone="+224622000099",
        permit_category="B",
        status="verified",
    )
    db.add(candidate)
    db.flush()
    session = ExamSession(
        reference=f"GN-SESSION-MEDIA-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5),
        capacity=35,
        status="open",
    )
    db.add(session)
    db.flush()
    return candidate, session


def test_legacy_bank_remains_runtime_compatible_but_never_strict_ready() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    questions = _bank(db, marker, legacy=True)
    db.commit()

    readiness = build_official_media_bank_readiness(db, questions)
    assert readiness["approved_questions"] == 40
    assert readiness["runtime_ready_questions"] == 40
    assert readiness["strict_ready_questions"] == 0
    assert readiness["runtime_exam_constructible"] is True
    assert readiness["strict_exam_constructible"] is False
    assert readiness["legacy_migration_required"] is True
    assert readiness["counts_by_mode"]["legacy_compatibility"] == 40
    db.close()


def test_pilot_switch_accepts_complete_legacy_bank(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    try:
        _isolate_active_question_bank(db)
        questions = _bank(db, marker, legacy=True)
        candidate, session = _candidate_session(db, marker)
        monkeypatch.setenv("OFFICIAL_MEDIA_STRICT_MODE", "false")

        readiness = build_official_media_bank_readiness(db, questions)
        assert readiness["runtime_exam_constructible"] is True
        assert readiness["strict_exam_constructible"] is False
        assert readiness["counts_by_mode"]["legacy_compatibility"] == 40

        attempt = create_media_safe_exam_attempt(
            db,
            candidate.id,
            session.id,
            commit=False,
        )
        trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt.id))
        assert trace is not None
        assert trace.question_count == 40
        assert trace.selection_mode == "official_category_distribution_media_safe"
    finally:
        db.rollback()
        db.close()


def test_strict_switch_refuses_complete_legacy_only_bank(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    try:
        _isolate_active_question_bank(db)
        questions = _bank(db, marker, legacy=True)
        candidate, session = _candidate_session(db, marker)
        monkeypatch.setenv("OFFICIAL_MEDIA_STRICT_MODE", "true")

        readiness = build_official_media_bank_readiness(db, questions)
        assert readiness["runtime_ready_questions"] == 40
        assert readiness["strict_ready_questions"] == 0
        assert readiness["runtime_exam_constructible"] is True
        assert readiness["strict_exam_constructible"] is False
        assert readiness["legacy_migration_required"] is True

        with pytest.raises(HTTPException) as exc_info:
            create_media_safe_exam_attempt(
                db,
                candidate.id,
                session.id,
                commit=False,
            )

        exc = exc_info.value
        assert exc.status_code == 503
        assert exc.detail["code"] == "OFFICIAL_MEDIA_BANK_NOT_READY"
        assert exc.detail["strict_mode"] is True
        assert exc.detail["media_gate"] == "strict_normalized_regulatory"
        assert exc.detail["runtime_ready_questions"] == 40
        assert exc.detail["strict_ready_questions"] == 0
        assert exc.detail["legacy_migration_required"] is True
    finally:
        db.rollback()
        db.close()


def test_strict_switch_accepts_full_normalized_image_video_bank(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    try:
        _isolate_active_question_bank(db)
        questions, primaries = _normalized_bank(db, marker)
        candidate, session = _candidate_session(db, marker)
        monkeypatch.setenv("OFFICIAL_MEDIA_STRICT_MODE", "true")

        image_assets = [asset for asset in primaries if asset.media_type == "image"]
        video_assets = [asset for asset in primaries if asset.media_type == "video"]
        assert len(image_assets) == 20
        assert len(video_assets) == 20
        assert all(asset.poster_media_id and asset.fallback_media_id for asset in video_assets)

        readiness = build_official_media_bank_readiness(db, questions)
        assert readiness["approved_questions"] == 40
        assert readiness["runtime_ready_questions"] == 40
        assert readiness["strict_ready_questions"] == 40
        assert readiness["runtime_exam_constructible"] is True
        assert readiness["strict_exam_constructible"] is True
        assert readiness["legacy_migration_required"] is False
        assert readiness["counts_by_mode"]["normalized_ready"] == 40

        attempt = create_media_safe_exam_attempt(
            db,
            candidate.id,
            session.id,
            commit=False,
        )
        trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt.id))
        assert trace is not None
        assert trace.question_count == 40
        assert trace.selection_mode == "official_category_distribution_media_strict"
    finally:
        db.rollback()
        db.close()


def test_normalized_primary_fails_closed_even_when_legacy_fallback_exists() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    question = _question(db, marker, "signalisation", 1, legacy=True)
    invalid_asset = _asset(db, marker, valid=False)
    db.add(QuestionMedia(question_id=question.id, media_id=invalid_asset.id, role="primary", display_order=0))
    db.commit()

    assessment = assess_official_question_media(db, question)
    assert assessment.mode == "normalized_blocked"
    assert assessment.runtime_ready is False
    assert assessment.strict_ready is False
    assert assessment.legacy_migration_required is False
    assert assessment.blockers
    db.close()


def test_valid_normalized_exam_asset_is_strict_ready() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    question = _question(db, marker, "signalisation", 1, legacy=False)
    asset = _asset(db, marker, valid=True)
    db.add(QuestionMedia(question_id=question.id, media_id=asset.id, role="primary", display_order=0))
    db.commit()

    assessment = assess_official_question_media(db, question)
    assert assessment.mode == "normalized_ready"
    assert assessment.runtime_ready is True
    assert assessment.strict_ready is True
    assert assessment.blockers == ()
    db.close()


def test_new_attempt_filters_unusable_media_and_blocks_incomplete_bank() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    questions = _bank(db, marker, legacy=True)
    candidate, session = _candidate_session(db, marker)

    # Une seule question entre dans la voie normalisée avec un média non validé.
    # La banque passe donc de 40 à 39 questions réellement éligibles.
    invalid_asset = _asset(db, f"invalid-{marker}", valid=False)
    db.add(QuestionMedia(question_id=questions[0].id, media_id=invalid_asset.id, role="primary", display_order=0))
    db.commit()

    try:
        create_media_safe_exam_attempt(db, candidate.id, session.id)
        raise AssertionError("La création devait être bloquée avec seulement 39 médias exploitables")
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail["code"] == "OFFICIAL_MEDIA_BANK_NOT_READY"
        assert exc.detail["runtime_ready_questions"] == 39
        assert exc.detail["required_questions"] == 40
    db.rollback()
    db.close()


def test_exam_router_uses_media_safe_attempt_creator_and_admin_readiness_endpoint() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    _bank(db, marker, legacy=True)
    admin = _admin(db, marker)
    headers = _headers(admin)
    db.commit()
    db.close()

    assert exams._create_exam_attempt is create_media_safe_exam_attempt

    with TestClient(app) as client:
        response = client.get("/api/v1/media-library/official-readiness", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["runtime_exam_constructible"] is True
        assert payload["legacy_migration_required"] is True
        assert payload["status"] == "runtime_ready_migration_required"
        assert payload["institutional_validation_inferred"] is False

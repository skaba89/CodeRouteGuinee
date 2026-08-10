"""Operational migration progress for normalized exam media.

The endpoint is admin-only and read-only. It measures actual question/media
state instead of inferring readiness from filenames or demo assets.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.media_quality import evaluate_media_asset
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from app.models_user import User

router = APIRouter()


@router.get("/migration-progress")
def media_migration_progress(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    question_rows = list(
        db.execute(select(Question.id, Question.media_type, Question.media_url)).all()
    )
    links = list(
        db.execute(
            select(QuestionMedia.question_id, MediaAsset)
            .join(MediaAsset, MediaAsset.id == QuestionMedia.media_id)
            .where(QuestionMedia.role == "primary")
            .order_by(QuestionMedia.question_id.asc(), QuestionMedia.display_order.asc(), QuestionMedia.created_at.asc())
        ).all()
    )

    primary_by_question: dict[str, MediaAsset] = {}
    for question_id, asset in links:
        primary_by_question.setdefault(str(question_id), asset)

    total = len(question_rows)
    normalized_primary = len(primary_by_question)
    publishable = 0
    normalized_blocked = 0
    generated_or_legacy_primary = 0
    image_primary = 0
    video_primary = 0
    blocked_question_ids: list[str] = []

    for question_id, asset in primary_by_question.items():
        if asset.media_type == "image":
            image_primary += 1
        elif asset.media_type == "video":
            video_primary += 1
        if asset.source_type in {"generated", "legacy"}:
            generated_or_legacy_primary += 1

        assessment = evaluate_media_asset(
            db,
            asset,
            require_quality_approval=True,
            require_regulatory_approval=True,
            require_exam_usage=True,
        )
        if assessment["passed"]:
            publishable += 1
        else:
            normalized_blocked += 1
            if len(blocked_question_ids) < 20:
                blocked_question_ids.append(question_id)

    legacy_only = 0
    no_media = 0
    normalized_ids = set(primary_by_question)
    for question_id, media_type, media_url in question_rows:
        if str(question_id) in normalized_ids:
            continue
        if (str(media_type or "").strip() and str(media_url or "").strip()):
            legacy_only += 1
        else:
            no_media += 1

    progress_percent = round((publishable / total * 100), 1) if total else 0.0
    normalized_percent = round((normalized_primary / total * 100), 1) if total else 0.0

    return {
        "total_questions": total,
        "normalized_primary": normalized_primary,
        "normalized_percent": normalized_percent,
        "publishable_premium": publishable,
        "publishable_percent": progress_percent,
        "normalized_blocked": normalized_blocked,
        "generated_or_legacy_primary": generated_or_legacy_primary,
        "legacy_only": legacy_only,
        "no_media": no_media,
        "by_primary_type": {
            "image": image_primary,
            "video": video_primary,
        },
        "blocked_question_ids_sample": blocked_question_ids,
        "definition": {
            "publishable_premium": "primary MediaAsset passes the full official exam quality + regulatory gate",
            "legacy_only": "no normalized primary; historical Question.media_* still present",
            "no_media": "no normalized primary and no historical media",
        },
        "institutional_validation_inferred": False,
    }

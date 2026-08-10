"""Actionable migration queue for normalized exam media.

Admin-only and read-only. The queue classifies real questions into four states
using the same media quality gate as the official exam runtime. It never maps a
media automatically and never infers institutional approval.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.media_quality import evaluate_media_asset
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from app.models_user import User

router = APIRouter()

_QUEUE_STATES = {"needs_action", "all", "publishable", "normalized_blocked", "legacy_only", "no_media"}
_STATE_PRIORITY = {
    "normalized_blocked": 0,
    "no_media": 2,
    "legacy_only": 3,
    "publishable": 9,
}


def _legacy_media_present(question: Question) -> bool:
    return bool(str(question.media_type or "").strip() and str(question.media_url or "").strip())


def _failed_check_codes(assessment: dict[str, Any]) -> list[str]:
    checks = assessment.get("checks") if isinstance(assessment.get("checks"), list) else []
    return [
        str(check.get("code"))
        for check in checks
        if isinstance(check, dict) and not check.get("passed") and check.get("code")
    ]


def _priority_rank(*, queue_state: str, validation_status: str) -> int:
    base = _STATE_PRIORITY[queue_state]
    # Already-approved questions are surfaced first because they may be selected
    # by the official exam engine today.
    return base if validation_status == "approved" else base + 10


def _next_action(queue_state: str, blocker_codes: list[str]) -> str:
    if queue_state == "legacy_only":
        return "Associer explicitement un MediaAsset primary validé à cette question."
    if queue_state == "no_media":
        return "Créer ou choisir un MediaAsset pertinent, le faire valider puis l’associer comme primary."
    if queue_state == "normalized_blocked":
        codes = ", ".join(blocker_codes[:4]) or "quality gate"
        return f"Corriger ou revalider le MediaAsset primary : {codes}."
    return "Aucune action média technique requise ; conserver les preuves de validation."


@router.get("/migration-queue")
def media_migration_queue(
    state_filter: str = Query(default="needs_action", max_length=32),
    category: str | None = Query(default=None, max_length=80),
    question_status: str | None = Query(default=None, max_length=20),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    normalized_state = state_filter.strip().lower()
    if normalized_state not in _QUEUE_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_MEDIA_MIGRATION_QUEUE_STATE",
                "allowed": sorted(_QUEUE_STATES),
            },
        )

    stmt = select(Question).order_by(Question.category.asc(), Question.created_at.desc(), Question.id.asc())
    if category:
        stmt = stmt.where(Question.category == category.strip())
    if question_status:
        stmt = stmt.where(Question.validation_status == question_status.strip().lower())
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Question.text.ilike(term), Question.category.ilike(term)))

    questions = list(db.scalars(stmt).all())
    question_ids = [question.id for question in questions]

    primary_by_question: dict[str, MediaAsset] = {}
    if question_ids:
        rows = list(
            db.execute(
                select(QuestionMedia.question_id, MediaAsset)
                .join(MediaAsset, MediaAsset.id == QuestionMedia.media_id)
                .where(
                    QuestionMedia.role == "primary",
                    QuestionMedia.question_id.in_(question_ids),
                )
                .order_by(
                    QuestionMedia.question_id.asc(),
                    QuestionMedia.display_order.asc(),
                    QuestionMedia.created_at.asc(),
                )
            ).all()
        )
        for question_id, asset in rows:
            primary_by_question.setdefault(str(question_id), asset)

    items: list[dict[str, Any]] = []
    counts = {"publishable": 0, "normalized_blocked": 0, "legacy_only": 0, "no_media": 0}

    for question in questions:
        asset = primary_by_question.get(question.id)
        assessment: dict[str, Any] | None = None
        blocker_codes: list[str] = []
        blocker_details: list[str] = []
        primary_media: dict[str, Any] | None = None

        if asset is not None:
            assessment = evaluate_media_asset(
                db,
                asset,
                require_quality_approval=True,
                require_regulatory_approval=True,
                require_exam_usage=True,
            )
            queue_state = "publishable" if assessment.get("passed") else "normalized_blocked"
            blocker_codes = _failed_check_codes(assessment)
            blocker_details = [str(value) for value in assessment.get("blockers", []) if value]
            primary_media = {
                "id": asset.id,
                "media_type": asset.media_type,
                "theme": asset.theme,
                "source_type": asset.source_type,
                "quality_status": asset.quality_status,
                "regulatory_status": asset.regulatory_status,
            }
        elif _legacy_media_present(question):
            queue_state = "legacy_only"
        else:
            queue_state = "no_media"

        counts[queue_state] += 1
        items.append(
            {
                "question_id": question.id,
                "category": question.category,
                "text": question.text,
                "validation_status": question.validation_status,
                "is_active": question.is_active,
                "queue_state": queue_state,
                "priority": "official_first" if question.validation_status == "approved" and queue_state != "publishable" else "normal",
                "legacy_media_present": _legacy_media_present(question),
                "legacy_media_type": question.media_type if _legacy_media_present(question) else None,
                "primary_media": primary_media,
                "blocker_codes": blocker_codes,
                "blocker_details": blocker_details,
                "next_action": _next_action(queue_state, blocker_codes),
                "_priority_rank": _priority_rank(
                    queue_state=queue_state,
                    validation_status=question.validation_status,
                ),
            }
        )

    if normalized_state == "needs_action":
        filtered = [item for item in items if item["queue_state"] != "publishable"]
    elif normalized_state == "all":
        filtered = items
    else:
        filtered = [item for item in items if item["queue_state"] == normalized_state]

    filtered.sort(key=lambda item: (item["_priority_rank"], item["category"], item["text"], item["question_id"]))
    total = len(filtered)
    page = filtered[offset : offset + limit]
    for item in page:
        item.pop("_priority_rank", None)

    return {
        "items": page,
        "total": total,
        "matched_questions": len(items),
        "limit": limit,
        "offset": offset,
        "state_filter": normalized_state,
        "counts_by_state": counts,
        "institutional_validation_inferred": False,
    }

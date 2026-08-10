"""Concurrency-safe and quality-gated manual QuestionMedia link creation.

Manual linking and transactional batch migration serialize on the same Question
row. A primary link must also pass the exact full official-exam media gate, so
the manual UI cannot bypass rights, technical quality, regulatory approval or
video poster/fallback requirements.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.media_quality import evaluate_media_asset
from app.models_audit import AuditLog
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from app.models_user import User
from app.schemas_media import QuestionMediaLinkCreate, QuestionMediaRead

router = APIRouter()


def _failed_check_codes(assessment: dict[str, Any]) -> list[str]:
    checks = assessment.get("checks") if isinstance(assessment.get("checks"), list) else []
    return [
        str(check.get("code"))
        for check in checks
        if isinstance(check, dict) and not check.get("passed") and check.get("code")
    ]


@router.post(
    "/media-library/questions/{question_id}/links",
    response_model=QuestionMediaRead,
    status_code=status.HTTP_201_CREATED,
)
def link_question_media_guard(
    question_id: str,
    payload: QuestionMediaLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> QuestionMedia:
    # The question is the serialization key shared with the transactional batch
    # migrator. PostgreSQL holds this row lock until commit/rollback.
    question = db.scalar(
        select(Question).where(Question.id == question_id).with_for_update()
    )
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")

    # Lock the asset too so an archive/update cannot race this association.
    asset = db.scalar(
        select(MediaAsset).where(MediaAsset.id == payload.media_id).with_for_update()
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Média introuvable")
    if asset.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Impossible d'associer un média archivé")

    # A normalized primary can affect the official candidate runtime immediately,
    # including for a question that was already approved before media migration.
    # Enforce the same gate as the batch migrator and official exam resolver now,
    # not only on a future Question.validation_status transition.
    if payload.role == "primary":
        assessment = evaluate_media_asset(
            db,
            asset,
            require_quality_approval=True,
            require_regulatory_approval=True,
            require_exam_usage=True,
        )
        if not assessment.get("passed"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "MEDIA_PRIMARY_NOT_PUBLISHABLE",
                    "message": "Le média principal ne passe pas le quality gate de l’examen officiel.",
                    "media_id": asset.id,
                    "score": assessment.get("score"),
                    "blocker_codes": _failed_check_codes(assessment),
                    "blockers": [str(value) for value in assessment.get("blockers", []) if value],
                    "institutional_validation_inferred": False,
                },
            )

    if payload.role in {"primary", "poster", "fallback"}:
        occupied = db.scalar(
            select(QuestionMedia)
            .where(
                QuestionMedia.question_id == question_id,
                QuestionMedia.role == payload.role,
            )
            .order_by(QuestionMedia.display_order.asc(), QuestionMedia.created_at.asc())
            .limit(1)
            .with_for_update()
        )
        if occupied:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": f"La question possède déjà un média {payload.role}",
                    "link_id": occupied.id,
                },
            )

    link = QuestionMedia(
        question_id=question_id,
        media_id=asset.id,
        role=payload.role,
        display_order=payload.display_order,
    )
    db.add(link)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Association média déjà existante") from exc

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="question.media_asset_linked",
            entity="question",
            entity_id=question_id,
            details={
                "media_id": asset.id,
                "role": payload.role,
                "display_order": payload.display_order,
                "concurrency_guard": "question_row_lock",
                "official_primary_gate_enforced": payload.role == "primary",
            },
        )
    )
    db.commit()
    db.refresh(link)
    return link

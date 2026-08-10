"""Explicit, transactional batch migration for question primary media.

The endpoint never infers mappings. Operators provide question_id -> media_id
pairs, run a dry-run, then explicitly apply the exact plan. Every primary media
must pass the same full quality/regulatory gate used by the official exam.
"""
from __future__ import annotations

from collections import Counter
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
from app.schemas_media_migration import MediaMigrationPlanEntry, MediaMigrationPlanRequest

router = APIRouter()

_READY_STATUSES = {"ready_create", "ready_replace", "no_op"}


def _failed_check_codes(assessment: dict[str, Any]) -> list[str]:
    checks = assessment.get("checks") if isinstance(assessment.get("checks"), list) else []
    return [
        str(check.get("code"))
        for check in checks
        if isinstance(check, dict) and not check.get("passed") and check.get("code")
    ]


def _question(db: Session, question_id: str, *, lock: bool) -> Question | None:
    if not lock:
        return db.get(Question, question_id)
    return db.scalar(select(Question).where(Question.id == question_id).with_for_update())


def _asset(db: Session, media_id: str, *, lock: bool) -> MediaAsset | None:
    if not lock:
        return db.get(MediaAsset, media_id)
    return db.scalar(select(MediaAsset).where(MediaAsset.id == media_id).with_for_update())


def _existing_primary(db: Session, question_id: str, *, lock: bool) -> QuestionMedia | None:
    stmt = (
        select(QuestionMedia)
        .where(QuestionMedia.question_id == question_id, QuestionMedia.role == "primary")
        .order_by(QuestionMedia.display_order.asc(), QuestionMedia.created_at.asc())
        .limit(1)
    )
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def _evaluate_mapping(
    db: Session,
    mapping: MediaMigrationPlanEntry,
    *,
    replace_existing: bool,
    lock: bool,
) -> tuple[dict[str, Any], Question | None, MediaAsset | None, QuestionMedia | None]:
    question = _question(db, mapping.question_id, lock=lock)
    if question is None:
        return (
            {
                "question_id": mapping.question_id,
                "media_id": mapping.media_id,
                "status": "missing_question",
                "ready": False,
                "blocker_codes": ["QUESTION_NOT_FOUND"],
                "blocker_details": ["La question n’existe pas."],
                "existing_primary_media_id": None,
            },
            None,
            None,
            None,
        )

    asset = _asset(db, mapping.media_id, lock=lock)
    if asset is None:
        return (
            {
                "question_id": mapping.question_id,
                "media_id": mapping.media_id,
                "status": "missing_media",
                "ready": False,
                "blocker_codes": ["MEDIA_NOT_FOUND"],
                "blocker_details": ["Le MediaAsset n’existe pas."],
                "existing_primary_media_id": None,
            },
            question,
            None,
            None,
        )

    assessment = evaluate_media_asset(
        db,
        asset,
        require_quality_approval=True,
        require_regulatory_approval=True,
        require_exam_usage=True,
    )
    existing = _existing_primary(db, mapping.question_id, lock=lock)
    blocker_codes = _failed_check_codes(assessment)
    blocker_details = [str(value) for value in assessment.get("blockers", []) if value]

    if not assessment.get("passed"):
        status_label = "blocked"
        ready = False
    elif existing is None:
        status_label = "ready_create"
        ready = True
    elif existing.media_id == mapping.media_id:
        status_label = "no_op"
        ready = True
    elif replace_existing:
        status_label = "ready_replace"
        ready = True
    else:
        status_label = "conflict_existing_primary"
        ready = False
        blocker_codes = [*blocker_codes, "PRIMARY_ALREADY_EXISTS"]
        blocker_details = [
            *blocker_details,
            f"Un primary existe déjà pour cette question : {existing.media_id}.",
        ]

    return (
        {
            "question_id": mapping.question_id,
            "media_id": mapping.media_id,
            "question_status": question.validation_status,
            "media_type": asset.media_type,
            "media_theme": asset.theme,
            "status": status_label,
            "ready": ready,
            "blocker_codes": blocker_codes,
            "blocker_details": blocker_details,
            "existing_primary_media_id": existing.media_id if existing else None,
        },
        question,
        asset,
        existing,
    )


def _summary(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(item.get("status") or "unknown") for item in items)
    return {
        "requested": len(items),
        "ready_create": counts["ready_create"],
        "ready_replace": counts["ready_replace"],
        "no_op": counts["no_op"],
        "blocked": counts["blocked"],
        "missing_question": counts["missing_question"],
        "missing_media": counts["missing_media"],
        "conflict_existing_primary": counts["conflict_existing_primary"],
    }


@router.post("/migration-plan")
def media_migration_plan(
    payload: MediaMigrationPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    if payload.replace_existing and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MEDIA_PRIMARY_REPLACEMENT_REQUIRES_SUPER_ADMIN",
                "message": "Le remplacement d’un primary existant est réservé au super_admin.",
            },
        )

    duplicate_questions = sorted(
        question_id
        for question_id, count in Counter(item.question_id for item in payload.mappings).items()
        if count > 1
    )
    if duplicate_questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "DUPLICATE_QUESTION_IN_MEDIA_MIGRATION_PLAN",
                "question_ids": duplicate_questions[:50],
            },
        )

    lock_rows = not payload.dry_run
    evaluated: list[tuple[dict[str, Any], Question | None, MediaAsset | None, QuestionMedia | None]] = []
    for mapping in payload.mappings:
        evaluated.append(
            _evaluate_mapping(
                db,
                mapping,
                replace_existing=payload.replace_existing,
                lock=lock_rows,
            )
        )

    items = [row[0] for row in evaluated]
    all_ready = all(item.get("status") in _READY_STATUSES for item in items)
    result = {
        "dry_run": payload.dry_run,
        "replace_existing": payload.replace_existing,
        "all_ready": all_ready,
        "applied": 0,
        "summary": _summary(items),
        "items": items,
        "institutional_validation_inferred": False,
    }

    if payload.dry_run:
        return result

    if not all_ready:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "MEDIA_MIGRATION_PLAN_NOT_READY",
                "message": "Le lot est refusé intégralement : au moins une association n’est pas prête.",
                "summary": result["summary"],
                "items": items[:100],
            },
        )

    applied = 0
    try:
        for public_item, question, asset, existing in evaluated:
            if public_item["status"] == "no_op":
                continue
            if question is None or asset is None:
                raise RuntimeError("validated migration row lost its question or media")

            old_media_id = existing.media_id if existing else None
            if existing is not None:
                db.delete(existing)
                db.flush()

            link = QuestionMedia(
                question_id=question.id,
                media_id=asset.id,
                role="primary",
                display_order=0,
            )
            db.add(link)
            db.flush()
            applied += 1

            db.add(
                AuditLog(
                    actor_id=current_user.id,
                    action="question.media_primary_batch_migrated",
                    entity="question",
                    entity_id=question.id,
                    details={
                        "new_media_id": asset.id,
                        "old_media_id": old_media_id,
                        "replace_existing": bool(old_media_id),
                        "reason": payload.reason,
                    },
                )
            )

        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="media_migration.plan_applied",
                entity="media_migration",
                entity_id="primary-batch",
                details={
                    "requested": len(payload.mappings),
                    "applied": applied,
                    "no_op": result["summary"]["no_op"],
                    "replace_existing": payload.replace_existing,
                    "reason": payload.reason,
                    "question_ids": [item.question_id for item in payload.mappings[:100]],
                },
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "MEDIA_MIGRATION_PLAN_CONCURRENT_CONFLICT",
                "message": "Le lot a été annulé car l’état des associations a changé pendant l’application.",
            },
        ) from exc

    result["applied"] = applied
    return result

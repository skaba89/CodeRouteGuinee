from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_question import Question
from app.models_user import User
from app.official_media_readiness import build_official_media_bank_readiness

router = APIRouter(prefix="/official-readiness", tags=["media-library"])


@router.get("")
def get_official_media_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    approved = list(
        db.scalars(
            select(Question).where(
                Question.is_active.is_(True),
                Question.validation_status == "approved",
            )
        ).all()
    )
    result = build_official_media_bank_readiness(db, approved)
    result["status"] = (
        "strict_ready"
        if result["strict_exam_constructible"] and not result["legacy_migration_required"]
        else "runtime_ready_migration_required"
        if result["runtime_exam_constructible"]
        else "blocked"
    )
    result["message"] = (
        "Banque média strictement prête pour un examen premium."
        if result["status"] == "strict_ready"
        else "Examen exécutable avec compatibilité legacy, migration média encore requise."
        if result["status"] == "runtime_ready_migration_required"
        else "Banque média insuffisante pour construire un nouvel examen officiel."
    )
    return result

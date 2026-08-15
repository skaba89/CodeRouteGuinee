"""Résumé fail-closed de la banque média pour le go-live national.

La validation détaillée reste centralisée dans ``official_media_readiness``.
Ce module expose seulement les compteurs et signaux nécessaires aux dashboards
et aux décisions de rollout, sans dupliquer les règles image/vidéo/homologation.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models_question import Question
from app.official_media_readiness import build_official_media_bank_readiness


def build_national_media_readiness(db: Session, questions: list[Question]) -> dict:
    readiness = build_official_media_bank_readiness(db, questions)
    counts_by_mode = dict(readiness.get("counts_by_mode") or {})
    legacy_remaining = int(counts_by_mode.get("legacy_compatibility", 0) or 0)

    return {
        "approved_questions": int(readiness.get("approved_questions", len(questions)) or 0),
        "runtime_ready_questions": int(readiness.get("runtime_ready_questions", 0) or 0),
        "strict_ready_questions": int(readiness.get("strict_ready_questions", 0) or 0),
        "runtime_exam_constructible": bool(readiness.get("runtime_exam_constructible")),
        "strict_exam_constructible": bool(readiness.get("strict_exam_constructible")),
        "legacy_migration_required": bool(readiness.get("legacy_migration_required")),
        "legacy_remaining": legacy_remaining,
        "counts_by_mode": counts_by_mode,
        "blocked_questions_total": int(readiness.get("blocked_questions_total", 0) or 0),
        # A technical PASS is never an institutional DNTT homologation.
        "institutional_validation_inferred": False,
    }


def national_media_strict_ready(readiness: dict) -> bool:
    return bool(readiness.get("strict_exam_constructible"))

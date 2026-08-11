"""Readiness rules for candidate-facing media in a new official exam.

This module deliberately separates two concepts:
- runtime compatibility: a controlled legacy image/video may still be served
  during migration so the pilot does not regress;
- premium go-live readiness: only normalized assets passing the full quality,
  rights, regulatory and exam-usage gate count as strict-ready.

No institutional approval is inferred from technical checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exam_engine import EXAM_QUESTIONS_TOTAL, select_exam_questions
from app.media_quality import evaluate_media_asset
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question


@dataclass(frozen=True)
class OfficialQuestionMediaReadiness:
    question_id: str
    runtime_ready: bool
    strict_ready: bool
    mode: str
    media_id: str | None
    blockers: tuple[str, ...]
    legacy_migration_required: bool

    def as_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "runtime_ready": self.runtime_ready,
            "strict_ready": self.strict_ready,
            "mode": self.mode,
            "media_id": self.media_id,
            "blockers": list(self.blockers),
            "legacy_migration_required": self.legacy_migration_required,
        }


def _legacy_delivery_is_usable(question: Question) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    media_type = (question.media_type or "").strip().lower()
    media_url = (question.media_url or "").strip()
    media_alt = (question.media_alt or "").strip()

    if media_type not in {"image", "video"}:
        blockers.append("LEGACY_MEDIA_TYPE: image ou video requis")
    parsed = urlparse(media_url) if media_url else None
    if not parsed or parsed.scheme != "https" or not parsed.netloc:
        blockers.append("LEGACY_DELIVERY_URL: URL HTTPS exploitable requise")
    if not media_alt:
        blockers.append("LEGACY_MEDIA_ALT: description candidate requise")
    return not blockers, blockers


def assess_official_question_media(db: Session, question: Question) -> OfficialQuestionMediaReadiness:
    primary = db.scalar(
        select(QuestionMedia)
        .where(QuestionMedia.question_id == question.id, QuestionMedia.role == "primary")
        .order_by(QuestionMedia.display_order.asc(), QuestionMedia.created_at.asc())
        .limit(1)
    )

    if primary is not None:
        asset = db.get(MediaAsset, primary.media_id)
        if asset is None:
            return OfficialQuestionMediaReadiness(
                question_id=question.id,
                runtime_ready=False,
                strict_ready=False,
                mode="normalized_blocked",
                media_id=primary.media_id,
                blockers=("PRIMARY_MEDIA_MISSING: média normalisé introuvable",),
                legacy_migration_required=False,
            )

        assessment = evaluate_media_asset(
            db,
            asset,
            require_quality_approval=True,
            require_regulatory_approval=True,
            require_exam_usage=True,
        )
        blockers = tuple(str(value) for value in assessment.get("blockers", []))
        passed = bool(assessment.get("passed"))
        # Une question entrée dans la voie normalisée ne retombe pas en legacy
        # pour un NOUVEL examen si le média devient invalide/archivé : cela
        # masquerait une régression de qualité ou de droits.
        return OfficialQuestionMediaReadiness(
            question_id=question.id,
            runtime_ready=passed,
            strict_ready=passed,
            mode="normalized_ready" if passed else "normalized_blocked",
            media_id=asset.id,
            blockers=blockers,
            legacy_migration_required=False,
        )

    legacy_ready, blockers = _legacy_delivery_is_usable(question)
    if legacy_ready:
        return OfficialQuestionMediaReadiness(
            question_id=question.id,
            runtime_ready=True,
            strict_ready=False,
            mode="legacy_compatibility",
            media_id=None,
            blockers=(),
            legacy_migration_required=True,
        )

    return OfficialQuestionMediaReadiness(
        question_id=question.id,
        runtime_ready=False,
        strict_ready=False,
        mode="media_missing_or_unusable",
        media_id=None,
        blockers=tuple(blockers or ["OFFICIAL_MEDIA_REQUIRED: média candidat exploitable absent"]),
        legacy_migration_required=True,
    )


def build_official_media_bank_readiness(db: Session, questions: list[Question]) -> dict:
    assessments = [assess_official_question_media(db, question) for question in questions]
    by_id = {item.question_id: item for item in assessments}
    runtime_questions = [question for question in questions if by_id[question.id].runtime_ready]
    strict_questions = [question for question in questions if by_id[question.id].strict_ready]

    runtime_selection = select_exam_questions(runtime_questions, seed="media-readiness-runtime")
    strict_selection = select_exam_questions(strict_questions, seed="media-readiness-strict")

    counts: dict[str, int] = {}
    for assessment in assessments:
        counts[assessment.mode] = counts.get(assessment.mode, 0) + 1

    blocked = [item.as_dict() for item in assessments if not item.runtime_ready]
    return {
        "approved_questions": len(questions),
        "runtime_ready_questions": len(runtime_questions),
        "strict_ready_questions": len(strict_questions),
        "runtime_exam_constructible": len(runtime_selection) == EXAM_QUESTIONS_TOTAL,
        "strict_exam_constructible": len(strict_selection) == EXAM_QUESTIONS_TOTAL,
        "legacy_migration_required": any(item.legacy_migration_required for item in assessments),
        "counts_by_mode": counts,
        "blocked_questions": blocked[:100],
        "blocked_questions_total": len(blocked),
        "institutional_validation_inferred": False,
    }


def runtime_ready_official_questions(db: Session, questions: list[Question]) -> tuple[list[Question], dict]:
    readiness = build_official_media_bank_readiness(db, questions)
    assessments = {question.id: assess_official_question_media(db, question) for question in questions}
    eligible = [question for question in questions if assessments[question.id].runtime_ready]
    return eligible, readiness

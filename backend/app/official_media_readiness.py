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


def _assess_with_primary(
    db: Session,
    question: Question,
    primary: QuestionMedia | None,
    asset: MediaAsset | None,
) -> OfficialQuestionMediaReadiness:
    if primary is not None:
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
        # masquerait une régression de qualité, de droits ou d'homologation.
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


def assess_official_question_media_batch(
    db: Session,
    questions: list[Question],
) -> list[OfficialQuestionMediaReadiness]:
    """Evaluate a bank with bounded SQL instead of one query per question.

    The common path performs one query for primary links and one for primary
    assets. Poster/fallback assets referenced by videos are prefetched in one
    additional query so ``evaluate_media_asset`` can resolve them from the
    SQLAlchemy identity map rather than issuing per-video lookups.
    """
    if not questions:
        return []

    question_ids = list(dict.fromkeys(question.id for question in questions))
    primary_rows = list(
        db.scalars(
            select(QuestionMedia)
            .where(
                QuestionMedia.question_id.in_(question_ids),
                QuestionMedia.role == "primary",
            )
            .order_by(
                QuestionMedia.question_id.asc(),
                QuestionMedia.display_order.asc(),
                QuestionMedia.created_at.asc(),
            )
        ).all()
    )

    primary_by_question: dict[str, QuestionMedia] = {}
    for row in primary_rows:
        primary_by_question.setdefault(row.question_id, row)

    primary_media_ids = list(
        dict.fromkeys(link.media_id for link in primary_by_question.values())
    )
    assets_by_id: dict[str, MediaAsset] = {}
    if primary_media_ids:
        primary_assets = list(
            db.scalars(select(MediaAsset).where(MediaAsset.id.in_(primary_media_ids))).all()
        )
        assets_by_id = {asset.id: asset for asset in primary_assets}

        support_ids = list(
            dict.fromkeys(
                media_id
                for asset in primary_assets
                for media_id in (asset.poster_media_id, asset.fallback_media_id)
                if media_id
            )
        )
        if support_ids:
            # Materialising this result warms the Session identity map for the
            # poster/fallback ``db.get`` calls inside the strict quality gate.
            list(db.scalars(select(MediaAsset).where(MediaAsset.id.in_(support_ids))).all())

    return [
        _assess_with_primary(
            db,
            question,
            primary_by_question.get(question.id),
            assets_by_id.get(primary_by_question[question.id].media_id)
            if question.id in primary_by_question
            else None,
        )
        for question in questions
    ]


def assess_official_question_media(
    db: Session,
    question: Question,
) -> OfficialQuestionMediaReadiness:
    return assess_official_question_media_batch(db, [question])[0]


def _build_readiness_from_assessments(
    questions: list[Question],
    assessments: list[OfficialQuestionMediaReadiness],
) -> dict:
    by_id = {item.question_id: item for item in assessments}
    runtime_questions = [
        question for question in questions if by_id[question.id].runtime_ready
    ]
    strict_questions = [
        question for question in questions if by_id[question.id].strict_ready
    ]

    runtime_selection = select_exam_questions(
        runtime_questions, seed="media-readiness-runtime"
    )
    strict_selection = select_exam_questions(
        strict_questions, seed="media-readiness-strict"
    )

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
        "legacy_migration_required": any(
            item.legacy_migration_required for item in assessments
        ),
        "counts_by_mode": counts,
        "blocked_questions": blocked[:100],
        "blocked_questions_total": len(blocked),
        "institutional_validation_inferred": False,
    }


def build_official_media_bank_readiness(
    db: Session,
    questions: list[Question],
) -> dict:
    assessments = assess_official_question_media_batch(db, questions)
    return _build_readiness_from_assessments(questions, assessments)


def _ready_official_questions(
    db: Session,
    questions: list[Question],
    *,
    strict: bool,
) -> tuple[list[Question], dict]:
    # The assessment is intentionally computed once. New exam creation may run
    # over hundreds or thousands of approved questions, so duplicating the
    # media preflight would double both CPU work and SQL reads.
    assessments = assess_official_question_media_batch(db, questions)
    by_id = {item.question_id: item for item in assessments}
    eligible = [
        question
        for question in questions
        if (by_id[question.id].strict_ready if strict else by_id[question.id].runtime_ready)
    ]
    readiness = _build_readiness_from_assessments(questions, assessments)
    return eligible, readiness


def runtime_ready_official_questions(
    db: Session,
    questions: list[Question],
) -> tuple[list[Question], dict]:
    return _ready_official_questions(db, questions, strict=False)


def strict_ready_official_questions(
    db: Session,
    questions: list[Question],
) -> tuple[list[Question], dict]:
    """Return only normalized questions ready for a national strict exam."""
    return _ready_official_questions(db, questions, strict=True)

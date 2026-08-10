"""Resolve the media that is safe to serve for an exam question.

The resolver is additive and migration-safe:
- a normalized primary MediaAsset is preferred only when it passes the full
  official-exam gate;
- a normalized asset that is draft/rejected/broken is never exposed;
- during the migration window, the historical Question.media_* values remain a
  controlled fallback so an already-operational question does not disappear;
- no provenance, licence, audit or authority metadata is exposed to candidates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.media_quality import evaluate_media_asset
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question


@dataclass(frozen=True)
class ResolvedExamMedia:
    question_id: str
    source: str
    media_type: str | None
    media_url: str | None
    media_alt: str | None
    poster_url: str | None = None
    fallback_url: str | None = None
    fallback_media_type: str | None = None
    degraded: bool = False
    fallback_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "source": self.source,
            "media_type": self.media_type,
            "media_url": self.media_url,
            "media_alt": self.media_alt,
            "poster_url": self.poster_url,
            "fallback_url": self.fallback_url,
            "fallback_media_type": self.fallback_media_type,
            "degraded": self.degraded,
            "fallback_reason": self.fallback_reason,
        }


def _delivery_url(asset: MediaAsset | None) -> str | None:
    if asset is None or asset.archived_at is not None:
        return None
    return (asset.secure_url or asset.public_url or "").strip() or None


def _safe_alt(question: Question, asset: MediaAsset | None = None) -> str:
    # Never synthesize an alt text that reveals the answer. The normalized
    # media schema does not yet carry reviewed candidate-facing alt text, so we
    # intentionally use a neutral description until the accessibility phase.
    if asset and asset.theme:
        return f"Situation de conduite — thème {asset.theme}"
    legacy = (question.media_alt or "").strip()
    if legacy:
        return legacy[:240]
    return "Situation de conduite"


def _legacy(question: Question, *, degraded: bool, reason: str | None) -> ResolvedExamMedia:
    media_type = (question.media_type or "").strip() or None
    media_url = (question.media_url or "").strip() or None
    if not media_type or not media_url:
        return ResolvedExamMedia(
            question_id=question.id,
            source="none",
            media_type=None,
            media_url=None,
            media_alt=None,
            degraded=degraded,
            fallback_reason=reason,
        )
    return ResolvedExamMedia(
        question_id=question.id,
        source="legacy",
        media_type=media_type,
        media_url=media_url,
        media_alt=_safe_alt(question),
        degraded=degraded,
        fallback_reason=reason,
    )


def resolve_exam_media(db: Session, question: Question) -> ResolvedExamMedia:
    link = db.scalar(
        select(QuestionMedia)
        .where(QuestionMedia.question_id == question.id, QuestionMedia.role == "primary")
        .order_by(QuestionMedia.display_order.asc(), QuestionMedia.created_at.asc())
        .limit(1)
    )
    if link is None:
        return _legacy(question, degraded=False, reason=None)

    asset = db.get(MediaAsset, link.media_id)
    if asset is None:
        return _legacy(question, degraded=True, reason="normalized_primary_missing")

    assessment = evaluate_media_asset(
        db,
        asset,
        require_quality_approval=True,
        require_regulatory_approval=True,
        require_exam_usage=True,
    )
    primary_url = _delivery_url(asset)
    if not assessment["passed"] or not primary_url:
        return _legacy(question, degraded=True, reason="normalized_primary_not_publishable")

    poster_url: str | None = None
    fallback_url: str | None = None
    fallback_type: str | None = None
    if asset.media_type == "video":
        poster = db.get(MediaAsset, asset.poster_media_id) if asset.poster_media_id else None
        fallback = db.get(MediaAsset, asset.fallback_media_id) if asset.fallback_media_id else None
        poster_url = _delivery_url(poster)
        fallback_url = _delivery_url(fallback)
        fallback_type = fallback.media_type if fallback and fallback_url else None
        # The official-exam quality gate already requires validated poster and
        # fallback. The extra runtime guard protects against an object becoming
        # unavailable between validation and delivery.
        if not poster_url or not fallback_url:
            return _legacy(question, degraded=True, reason="normalized_video_support_media_unavailable")

    return ResolvedExamMedia(
        question_id=question.id,
        source="normalized",
        media_type=asset.media_type,
        media_url=primary_url,
        media_alt=_safe_alt(question, asset),
        poster_url=poster_url,
        fallback_url=fallback_url,
        fallback_media_type=fallback_type,
        degraded=False,
        fallback_reason=None,
    )


def resolve_exam_media_batch(db: Session, question_ids: Iterable[str]) -> list[ResolvedExamMedia]:
    ids = [str(value).strip() for value in question_ids if str(value).strip()]
    if not ids:
        return []
    unique_ids = list(dict.fromkeys(ids))[:200]
    questions = list(db.scalars(select(Question).where(Question.id.in_(unique_ids))).all())
    by_id = {question.id: question for question in questions}
    result: list[ResolvedExamMedia] = []
    for question_id in unique_ids:
        question = by_id.get(question_id)
        if question is None:
            result.append(
                ResolvedExamMedia(
                    question_id=question_id,
                    source="none",
                    media_type=None,
                    media_url=None,
                    media_alt=None,
                    degraded=True,
                    fallback_reason="question_missing",
                )
            )
            continue
        result.append(resolve_exam_media(db, question))
    return result

"""Premium media quality gate for exam publication.

Automated checks prove technical facts only. Human pedagogical and regulatory
approval remain explicit statuses and are never inferred by this module.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_media import MediaAsset, QuestionMedia

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _delivery_url(asset: MediaAsset) -> str | None:
    return (asset.secure_url or asset.public_url or "").strip() or None


def _linked_asset(db: Session, media_id: str | None) -> MediaAsset | None:
    return db.get(MediaAsset, media_id) if media_id else None


def evaluate_media_asset(
    db: Session,
    asset: MediaAsset,
    *,
    require_quality_approval: bool = True,
    require_regulatory_approval: bool = False,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    score = 0

    def check(code: str, passed: bool, detail: str, points: int = 0) -> None:
        nonlocal score
        item = {"code": code, "passed": bool(passed), "detail": detail, "points": points if passed else 0, "max_points": points}
        checks.append(item)
        if passed:
            score += points
        else:
            blockers.append(f"{code}: {detail}")

    check("NOT_ARCHIVED", asset.archived_at is None, "média actif" if asset.archived_at is None else "média archivé")
    check("EXAM_USAGE", asset.usage_type == "exam", f"usage_type={asset.usage_type}")
    check("DELIVERY_URL", bool(_delivery_url(asset)), "URL de livraison présente" if _delivery_url(asset) else "URL de livraison absente", 5)
    check(
        "CHECKSUM_SHA256",
        bool(asset.checksum_sha256 and _SHA256_RE.fullmatch(asset.checksum_sha256.lower())),
        "SHA-256 présent" if asset.checksum_sha256 else "SHA-256 absent",
        5,
    )

    allowed_mime = {
        "image": {"image/jpeg", "image/png", "image/webp", "image/avif"},
        "video": {"video/mp4", "video/webm", "video/quicktime"},
        "audio": {"audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav", "audio/x-wav", "audio/webm"},
    }
    mime_ok = bool(asset.mime_type and asset.mime_type.lower() in allowed_mime.get(asset.media_type, set()))
    check("FORMAT", mime_ok, f"mime_type={asset.mime_type or 'missing'}", 10)

    if asset.media_type in {"image", "video"}:
        resolution_ok = bool((asset.width or 0) >= 1280 and (asset.height or 0) >= 720)
        check("HD_RESOLUTION", resolution_ok, f"résolution={asset.width or 0}x{asset.height or 0}, minimum=1280x720", 20)
        ratio = (float(asset.width) / float(asset.height)) if asset.width and asset.height else 0.0
        mobile_ok = bool(1.3 <= ratio <= 2.0)
        check("MOBILE_READABILITY", mobile_ok, f"ratio={ratio:.2f}" if ratio else "ratio inconnu", 10)
    else:
        check("HD_RESOLUTION", True, "non applicable à l'audio", 20)
        check("MOBILE_READABILITY", True, "non applicable à l'audio", 10)

    if asset.media_type == "video":
        duration_ok = bool(asset.duration_seconds is not None and 6 <= asset.duration_seconds <= 20)
        check("EXAM_VIDEO_DURATION", duration_ok, f"durée={asset.duration_seconds!r}s, cible=6-20s")
        poster = _linked_asset(db, asset.poster_media_id)
        fallback = _linked_asset(db, asset.fallback_media_id)
        poster_ok = bool(poster and poster.archived_at is None and poster.media_type == "image" and poster.quality_status == "validated")
        fallback_ok = bool(fallback and fallback.archived_at is None and fallback.media_type == "image" and fallback.quality_status == "validated")
        check("VIDEO_POSTER_VALIDATED", poster_ok, "poster image validé" if poster_ok else "poster image validé obligatoire")
        check("VIDEO_FALLBACK_VALIDATED", fallback_ok, "fallback image validé" if fallback_ok else "fallback image validé obligatoire")

    source_ok = asset.source_type in {"original", "licensed", "partner", "public_domain", "internal"}
    check("SOURCE_TRACEABLE", source_ok, f"source_type={asset.source_type}")

    if asset.source_type in {"licensed", "partner"}:
        rights_ok = bool(asset.license_reference and asset.copyright_owner)
    elif asset.source_type == "public_domain":
        rights_ok = bool(asset.source_reference)
    elif asset.source_type in {"original", "internal"}:
        rights_ok = bool(asset.source_reference or asset.copyright_owner)
    else:
        rights_ok = False

    if asset.license_expiration_date and asset.license_expiration_date < date.today():
        rights_ok = False
    check("RIGHTS_TRACEABLE", rights_ok, "droits/provenance documentés" if rights_ok else "preuve de droits insuffisante ou expirée", 15)

    if require_quality_approval:
        quality_ok = asset.quality_status == "validated"
        check("PEDAGOGICAL_QUALITY_APPROVED", quality_ok, f"quality_status={asset.quality_status}", 20)
    else:
        check("PEDAGOGICAL_QUALITY_APPROVED", True, f"quality_status={asset.quality_status} (non exigé à cette étape)", 20)

    if require_regulatory_approval:
        regulatory_ok = asset.regulatory_status == "validated" and bool(asset.regulatory_authority_reference)
        check(
            "REGULATORY_APPROVED",
            regulatory_ok,
            f"regulatory_status={asset.regulatory_status}; authority_ref={'présente' if asset.regulatory_authority_reference else 'absente'}",
            20,
        )
    else:
        check("REGULATORY_APPROVED", True, f"regulatory_status={asset.regulatory_status} (non exigé à cette étape)", 20)

    return {
        "media_id": asset.id,
        "passed": not blockers,
        "score": min(score, 100),
        "checks": checks,
        "blockers": blockers,
        "human_review_required": True,
        "institutional_validation_inferred": False,
    }


def evaluate_question_media_gate(
    db: Session,
    question_id: str,
    *,
    require_regulatory_approval: bool,
) -> dict[str, Any]:
    primary_link = db.scalar(
        select(QuestionMedia)
        .where(QuestionMedia.question_id == question_id, QuestionMedia.role == "primary")
        .order_by(QuestionMedia.display_order.asc(), QuestionMedia.created_at.asc())
        .limit(1)
    )
    if primary_link is None:
        return {
            "question_id": question_id,
            "mode": "legacy_compatibility",
            "passed": True,
            "media_id": None,
            "score": None,
            "checks": [],
            "blockers": [],
            "legacy_migration_required": True,
        }

    asset = db.get(MediaAsset, primary_link.media_id)
    if asset is None:
        return {
            "question_id": question_id,
            "mode": "normalized",
            "passed": False,
            "media_id": primary_link.media_id,
            "score": 0,
            "checks": [],
            "blockers": ["PRIMARY_MEDIA_MISSING: le média principal associé est introuvable"],
            "legacy_migration_required": False,
        }

    result = evaluate_media_asset(
        db,
        asset,
        require_quality_approval=True,
        require_regulatory_approval=require_regulatory_approval,
    )
    return {
        "question_id": question_id,
        "mode": "normalized",
        "legacy_migration_required": False,
        **result,
    }

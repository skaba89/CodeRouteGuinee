from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.media_quality import evaluate_media_asset, evaluate_question_media_gate
from app.models_audit import AuditLog
from app.models_media import MediaAsset
from app.models_user import User
from app.schemas_media import MediaAssetRead
from app.schemas_media_review import MediaQualityGateRead, MediaRegulatoryApprovalRequest, MediaReviewRequest

router = APIRouter(prefix="/media-library", tags=["media-library-review"])


def _asset_or_404(db: Session, media_id: str) -> MediaAsset:
    asset = db.get(MediaAsset, media_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Média introuvable")
    return asset


def _ensure_active(asset: MediaAsset) -> None:
    if asset.archived_at is not None:
        raise HTTPException(status_code=409, detail="Un média archivé ne peut pas être validé")


def _four_eyes(asset: MediaAsset, reviewer: User) -> None:
    if asset.created_by and asset.created_by == reviewer.id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MEDIA_FOUR_EYES_REQUIRED",
                "message": "Le créateur du média ne peut pas être son validateur final.",
            },
        )


def _audit(db: Session, *, actor_id: str, action: str, asset: MediaAsset, details: dict) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity="media_asset",
            entity_id=asset.id,
            details=details,
        )
    )


@router.get("/assets/{media_id}/quality-gate", response_model=MediaQualityGateRead)
def asset_quality_gate(
    media_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    asset = _asset_or_404(db, media_id)
    return evaluate_media_asset(
        db,
        asset,
        require_quality_approval=True,
        require_regulatory_approval=True,
    )


@router.post("/assets/{media_id}/quality/submit", response_model=MediaAssetRead)
def submit_quality_review(
    media_id: str,
    payload: MediaReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAsset:
    asset = _asset_or_404(db, media_id)
    _ensure_active(asset)
    if asset.quality_status == "validated":
        raise HTTPException(status_code=409, detail="Le média est déjà validé en qualité")
    asset.quality_status = "review_required"
    asset.validated_by = None
    asset.validated_at = None
    _audit(
        db,
        actor_id=current_user.id,
        action="media_asset.quality_submitted",
        asset=asset,
        details={"reason": payload.reason.strip()},
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{media_id}/quality/approve", response_model=MediaAssetRead)
def approve_quality_review(
    media_id: str,
    payload: MediaReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAsset:
    asset = _asset_or_404(db, media_id)
    _ensure_active(asset)
    _four_eyes(asset, current_user)
    if asset.quality_status != "review_required":
        raise HTTPException(status_code=409, detail="Le média doit d'abord être soumis en revue qualité")

    technical = evaluate_media_asset(
        db,
        asset,
        require_quality_approval=False,
        require_regulatory_approval=False,
    )
    if not technical["passed"]:
        raise HTTPException(
            status_code=409,
            detail={"code": "MEDIA_TECHNICAL_GATE_BLOCKED", "blockers": technical["blockers"]},
        )

    asset.quality_status = "validated"
    asset.validated_by = current_user.id
    asset.validated_at = datetime.now(UTC).replace(tzinfo=None)
    _audit(
        db,
        actor_id=current_user.id,
        action="media_asset.quality_approved",
        asset=asset,
        details={"reason": payload.reason.strip(), "score": technical["score"]},
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{media_id}/quality/reject", response_model=MediaAssetRead)
def reject_quality_review(
    media_id: str,
    payload: MediaReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAsset:
    asset = _asset_or_404(db, media_id)
    _ensure_active(asset)
    _four_eyes(asset, current_user)
    asset.quality_status = "rejected"
    asset.regulatory_status = "not_reviewed"
    asset.regulatory_authority_reference = None
    asset.validated_by = current_user.id
    asset.validated_at = datetime.now(UTC).replace(tzinfo=None)
    _audit(
        db,
        actor_id=current_user.id,
        action="media_asset.quality_rejected",
        asset=asset,
        details={"reason": payload.reason.strip()},
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{media_id}/regulatory/submit", response_model=MediaAssetRead)
def submit_regulatory_review(
    media_id: str,
    payload: MediaReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAsset:
    asset = _asset_or_404(db, media_id)
    _ensure_active(asset)
    if asset.quality_status != "validated":
        raise HTTPException(status_code=409, detail="La qualité pédagogique doit être validée avant la revue réglementaire")
    if asset.regulatory_status == "validated":
        raise HTTPException(status_code=409, detail="Le média est déjà validé réglementairement")
    asset.regulatory_status = "under_review"
    asset.regulatory_authority_reference = None
    _audit(
        db,
        actor_id=current_user.id,
        action="media_asset.regulatory_submitted",
        asset=asset,
        details={"reason": payload.reason.strip()},
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{media_id}/regulatory/approve", response_model=MediaAssetRead)
def approve_regulatory_review(
    media_id: str,
    payload: MediaRegulatoryApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> MediaAsset:
    asset = _asset_or_404(db, media_id)
    _ensure_active(asset)
    _four_eyes(asset, current_user)
    if asset.quality_status != "validated" or asset.regulatory_status != "under_review":
        raise HTTPException(status_code=409, detail="Le média doit être validé en qualité et soumis en revue réglementaire")

    gate = evaluate_media_asset(
        db,
        asset,
        require_quality_approval=True,
        require_regulatory_approval=False,
    )
    if not gate["passed"]:
        raise HTTPException(
            status_code=409,
            detail={"code": "MEDIA_QUALITY_GATE_BLOCKED", "blockers": gate["blockers"]},
        )

    asset.regulatory_status = "validated"
    asset.regulatory_authority_reference = payload.authority_reference.strip()
    asset.validated_by = current_user.id
    asset.validated_at = datetime.now(UTC).replace(tzinfo=None)
    _audit(
        db,
        actor_id=current_user.id,
        action="media_asset.regulatory_approved",
        asset=asset,
        details={
            "reason": payload.reason.strip(),
            "authority_reference": payload.authority_reference.strip(),
            "score": gate["score"],
        },
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{media_id}/regulatory/reject", response_model=MediaAssetRead)
def reject_regulatory_review(
    media_id: str,
    payload: MediaReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> MediaAsset:
    asset = _asset_or_404(db, media_id)
    _ensure_active(asset)
    asset.regulatory_status = "rejected"
    asset.regulatory_authority_reference = None
    asset.validated_by = current_user.id
    asset.validated_at = datetime.now(UTC).replace(tzinfo=None)
    _audit(
        db,
        actor_id=current_user.id,
        action="media_asset.regulatory_rejected",
        asset=asset,
        details={"reason": payload.reason.strip()},
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/questions/{question_id}/quality-gate")
def question_quality_gate(
    question_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return evaluate_question_media_gate(db, question_id, require_regulatory_approval=True)

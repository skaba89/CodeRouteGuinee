from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.media_storage import (
    MediaStorageError,
    MediaStorageValidationError,
    get_media_storage_provider,
)
from app.media_validation import validate_asset_metadata, validation_sensitive_changes
from app.models_audit import AuditLog
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from app.models_user import User
from app.schemas_media import (
    MediaAssetCreate,
    MediaAssetList,
    MediaAssetRead,
    MediaAssetUpdate,
    MediaUploadTargetRequest,
    MediaUploadTargetResponse,
    QuestionMediaLinkCreate,
    QuestionMediaRead,
)

router = APIRouter(prefix="/media-library", tags=["media-library"])

_ASSET_MUTABLE_FIELDS = {
    "media_type",
    "usage_type",
    "storage_provider",
    "storage_key",
    "public_url",
    "secure_url",
    "mime_type",
    "width",
    "height",
    "duration_seconds",
    "file_size_bytes",
    "checksum_sha256",
    "poster_media_id",
    "fallback_media_id",
    "theme",
    "subtheme",
    "country_code",
    "regulatory_scope",
    "source_type",
    "source_reference",
    "license_type",
    "license_reference",
    "license_expiration_date",
    "copyright_owner",
}


def _asset_or_404(db: Session, media_id: str) -> MediaAsset:
    asset = db.get(MediaAsset, media_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Média introuvable")
    return asset


def _question_or_404(db: Session, question_id: str) -> Question:
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")
    return question


def _validate_media_references(db: Session, values: dict, *, current_asset_id: str | None = None) -> None:
    for field in ("poster_media_id", "fallback_media_id"):
        ref = values.get(field)
        if not ref:
            continue
        if current_asset_id and ref == current_asset_id:
            raise HTTPException(status_code=422, detail=f"{field} ne peut pas référencer le média lui-même")
        linked = db.get(MediaAsset, ref)
        if not linked or linked.archived_at is not None:
            raise HTTPException(status_code=422, detail=f"{field} référence un média absent ou archivé")
        if linked.media_type != "image":
            raise HTTPException(status_code=422, detail=f"{field} doit référencer une image")


def _full_asset_values(asset: MediaAsset) -> dict:
    return {field: getattr(asset, field) for field in _ASSET_MUTABLE_FIELDS}


def _audit(db: Session, *, user_id: str, action: str, entity_id: str, details: dict) -> None:
    db.add(
        AuditLog(
            actor_id=user_id,
            action=action,
            entity="media_asset",
            entity_id=entity_id,
            details=details,
        )
    )


@router.get("/assets", response_model=MediaAssetList)
def list_media_assets(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    media_type: str | None = Query(default=None),
    usage_type: str | None = Query(default=None),
    quality_status: str | None = Query(default=None),
    regulatory_status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    theme: str | None = Query(default=None, max_length=80),
    search: str | None = Query(default=None, max_length=160),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAssetList:
    stmt = select(MediaAsset).order_by(MediaAsset.created_at.desc())
    if not include_archived:
        stmt = stmt.where(MediaAsset.archived_at.is_(None))
    if media_type:
        stmt = stmt.where(MediaAsset.media_type == media_type.strip().lower())
    if usage_type:
        stmt = stmt.where(MediaAsset.usage_type == usage_type.strip().lower())
    if quality_status:
        stmt = stmt.where(MediaAsset.quality_status == quality_status.strip().lower())
    if regulatory_status:
        stmt = stmt.where(MediaAsset.regulatory_status == regulatory_status.strip().lower())
    if source_type:
        stmt = stmt.where(MediaAsset.source_type == source_type.strip().lower())
    if theme:
        stmt = stmt.where(MediaAsset.theme == theme.strip())
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                MediaAsset.theme.ilike(term),
                MediaAsset.subtheme.ilike(term),
                MediaAsset.source_reference.ilike(term),
                MediaAsset.copyright_owner.ilike(term),
                MediaAsset.storage_key.ilike(term),
            )
        )

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    return MediaAssetList(
        items=[MediaAssetRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/assets/{media_id}", response_model=MediaAssetRead)
def get_media_asset(
    media_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAsset:
    return _asset_or_404(db, media_id)


@router.post("/assets", response_model=MediaAssetRead, status_code=status.HTTP_201_CREATED)
def create_media_asset(
    payload: MediaAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAsset:
    data = payload.model_dump()
    try:
        data = validate_asset_metadata(data, media_type=payload.media_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _validate_media_references(db, data)

    checksum = data.get("checksum_sha256")
    if checksum:
        duplicate = db.scalar(
            select(MediaAsset).where(
                MediaAsset.checksum_sha256 == checksum,
                MediaAsset.archived_at.is_(None),
            ).limit(1)
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Ce fichier existe déjà dans la médiathèque", "media_id": duplicate.id},
            )

    asset = MediaAsset(
        **data,
        quality_status="draft",
        regulatory_status="not_reviewed",
        created_by=current_user.id,
    )
    db.add(asset)
    db.flush()
    _audit(
        db,
        user_id=current_user.id,
        action="media_asset.created",
        entity_id=asset.id,
        details={
            "media_type": asset.media_type,
            "usage_type": asset.usage_type,
            "source_type": asset.source_type,
            "has_checksum": bool(asset.checksum_sha256),
            "storage_provider": asset.storage_provider,
        },
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/assets/{media_id}", response_model=MediaAssetRead)
def update_media_asset(
    media_id: str,
    payload: MediaAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAsset:
    asset = _asset_or_404(db, media_id)
    if asset.archived_at is not None:
        raise HTTPException(status_code=409, detail="Un média archivé ne peut pas être modifié")

    requested = payload.model_dump(exclude_unset=True)
    if not requested:
        return asset

    candidate = _full_asset_values(asset)
    candidate.update(requested)
    candidate_type = str(candidate.get("media_type") or asset.media_type)
    try:
        normalized = validate_asset_metadata(candidate, media_type=candidate_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    changes = {key: normalized.get(key) for key in requested}
    _validate_media_references(db, normalized, current_asset_id=asset.id)
    sensitive = validation_sensitive_changes(asset, changes)

    checksum = changes.get("checksum_sha256")
    if checksum and checksum != asset.checksum_sha256:
        duplicate = db.scalar(
            select(MediaAsset).where(
                MediaAsset.id != asset.id,
                MediaAsset.checksum_sha256 == checksum,
                MediaAsset.archived_at.is_(None),
            ).limit(1)
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail={"message": "Ce fichier existe déjà dans la médiathèque", "media_id": duplicate.id},
            )

    for key, value in changes.items():
        setattr(asset, key, value)

    invalidated = False
    if sensitive:
        if asset.quality_status in {"validated", "rejected"}:
            asset.quality_status = "review_required"
            invalidated = True
        if asset.regulatory_status in {"validated", "rejected"}:
            asset.regulatory_status = "under_review"
            invalidated = True
        if invalidated:
            asset.validated_by = None
            asset.validated_at = None

    asset.updated_at = datetime.now(UTC).replace(tzinfo=None)
    _audit(
        db,
        user_id=current_user.id,
        action="media_asset.updated",
        entity_id=asset.id,
        details={
            "changed_fields": sorted(changes),
            "validation_sensitive_fields": sorted(sensitive),
            "validation_invalidated": invalidated,
        },
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{media_id}/archive", response_model=MediaAssetRead)
def archive_media_asset(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaAsset:
    asset = _asset_or_404(db, media_id)
    if asset.archived_at is None:
        asset.archived_at = datetime.now(UTC).replace(tzinfo=None)
        _audit(
            db,
            user_id=current_user.id,
            action="media_asset.archived",
            entity_id=asset.id,
            details={"quality_status": asset.quality_status, "regulatory_status": asset.regulatory_status},
        )
        db.commit()
        db.refresh(asset)
    return asset


@router.post("/upload-target", response_model=MediaUploadTargetResponse)
def create_upload_target(
    payload: MediaUploadTargetRequest,
    provider: str | None = Query(default=None, max_length=40),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> MediaUploadTargetResponse:
    try:
        storage = get_media_storage_provider(provider)
        target = storage.build_upload_target(
            media_type=payload.media_type,
            filename=payload.filename,
            content_type=payload.content_type,
        )
    except MediaStorageValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MediaStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return MediaUploadTargetResponse(**target.as_dict())


@router.get("/questions/{question_id}", response_model=list[QuestionMediaRead])
def list_question_media(
    question_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[QuestionMedia]:
    _question_or_404(db, question_id)
    return list(
        db.scalars(
            select(QuestionMedia)
            .where(QuestionMedia.question_id == question_id)
            .order_by(QuestionMedia.role.asc(), QuestionMedia.display_order.asc(), QuestionMedia.created_at.asc())
        ).all()
    )


@router.post("/questions/{question_id}/links", response_model=QuestionMediaRead, status_code=201)
def link_question_media(
    question_id: str,
    payload: QuestionMediaLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> QuestionMedia:
    _question_or_404(db, question_id)
    asset = _asset_or_404(db, payload.media_id)
    if asset.archived_at is not None:
        raise HTTPException(status_code=409, detail="Impossible d'associer un média archivé")

    if payload.role in {"primary", "poster", "fallback"}:
        occupied = db.scalar(
            select(QuestionMedia).where(
                QuestionMedia.question_id == question_id,
                QuestionMedia.role == payload.role,
            ).limit(1)
        )
        if occupied:
            raise HTTPException(
                status_code=409,
                detail={"message": f"La question possède déjà un média {payload.role}", "link_id": occupied.id},
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
        raise HTTPException(status_code=409, detail="Association média déjà existante") from exc

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="question.media_asset_linked",
            entity="question",
            entity_id=question_id,
            details={"media_id": asset.id, "role": payload.role, "display_order": payload.display_order},
        )
    )
    db.commit()
    db.refresh(link)
    return link


@router.delete(
    "/questions/{question_id}/links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def unlink_question_media(
    question_id: str,
    link_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> None:
    _question_or_404(db, question_id)
    link = db.get(QuestionMedia, link_id)
    if not link or link.question_id != question_id:
        raise HTTPException(status_code=404, detail="Association média introuvable")
    media_id = link.media_id
    role = link.role
    db.delete(link)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="question.media_asset_unlinked",
            entity="question",
            entity_id=question_id,
            details={"media_id": media_id, "role": role},
        )
    )
    db.commit()
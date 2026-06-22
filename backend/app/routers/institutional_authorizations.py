from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_user import User
from app.schemas import InstitutionalAuthorizationCreate, InstitutionalAuthorizationRead, InstitutionalAuthorizationStatusUpdate

router = APIRouter(prefix="/institutional-authorizations", tags=["institutional-authorizations"])


@router.get("", response_model=dict)
def list_authorizations(
    status_filter: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[InstitutionalAuthorization]:
    query = select(InstitutionalAuthorization)
    if status_filter:
        query = query.where(InstitutionalAuthorization.status == status_filter)
    query = query.order_by(InstitutionalAuthorization.created_at.desc()).limit(max(1, min(limit, 200)))
    if search:
        from sqlalchemy import or_
        query = query.where(
            or_(
                InstitutionalAuthorization.authority.ilike(f"%{search}%"),
                InstitutionalAuthorization.title.ilike(f"%{search}%"),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    raw_items = list(db.scalars(query.offset(offset).limit(max(1, min(limit, 200)))).all())
    items = [InstitutionalAuthorizationRead.model_validate(x) for x in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.post("", response_model=InstitutionalAuthorizationRead, status_code=status.HTTP_201_CREATED)
def create_authorization(
    payload: InstitutionalAuthorizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> InstitutionalAuthorization:
    authorization = InstitutionalAuthorization(**payload.model_dump(), status="draft")
    db.add(authorization)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="institutional_authorization.created",
            entity="institutional_authorization",
            entity_id=authorization.id,
            details={"authority": authorization.authority, "reference": authorization.reference, "status": authorization.status},
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Authorization reference already exists") from exc
    db.refresh(authorization)
    return authorization


@router.patch("/{authorization_id}/status", response_model=InstitutionalAuthorizationRead)
def update_authorization_status(
    authorization_id: str,
    payload: InstitutionalAuthorizationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> InstitutionalAuthorization:
    authorization = db.get(InstitutionalAuthorization, authorization_id)
    if not authorization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institutional authorization not found")

    previous_status = authorization.status
    authorization.status = payload.status
    authorization.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(authorization)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="institutional_authorization.status_updated",
            entity="institutional_authorization",
            entity_id=authorization.id,
            details={
                "authority": authorization.authority,
                "reference": authorization.reference,
                "previous_status": previous_status,
                "new_status": payload.status,
                "reason": payload.reason,
            },
        )
    )
    db.commit()
    db.refresh(authorization)
    return authorization

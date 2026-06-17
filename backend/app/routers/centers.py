from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_user import User
from app.schemas import CenterCreate, CenterRead, CenterStatusUpdate

router = APIRouter(prefix="/centers", tags=["centers"])


@router.get("", response_model=list[CenterRead])
def list_centers(db: Session = Depends(get_db)) -> list[Center]:
    return list(db.scalars(select(Center).order_by(Center.created_at.desc())).all())


@router.post("", response_model=CenterRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin", "super_admin"))])
def create_center(payload: CenterCreate, db: Session = Depends(get_db)) -> Center:
    center = Center(**payload.model_dump())
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


@router.patch("/{center_id}/status", response_model=CenterRead)
def update_center_status(
    center_id: str,
    payload: CenterStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Center:
    center = db.get(Center, center_id)
    if not center:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Center not found")
    previous_status = center.status
    center.status = payload.status
    db.add(center)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="center.status_updated",
            entity="center",
            entity_id=center.id,
            details={
                "code": center.code,
                "previous_status": previous_status,
                "new_status": payload.status,
                "reason": payload.reason,
            },
        )
    )
    db.commit()
    db.refresh(center)
    return center

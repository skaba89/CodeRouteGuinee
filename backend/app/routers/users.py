from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_user import User
from app.schemas import UserRead, UserRoleUpdate, UserStatusUpdate

router = APIRouter(prefix="/users", tags=["users"])


def audit_user_decision(
    db: Session,
    current_user: User,
    target_user: User,
    action: str,
    reason: str,
    previous_value: str | bool,
    new_value: str | bool,
) -> None:
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=action,
            entity="user",
            entity_id=target_user.id,
            details={
                "email": target_user.email,
                "previous_value": previous_value,
                "new_value": new_value,
                "reason": reason,
            },
        )
    )


@router.get("", response_model=list[UserRead])
def list_users(
    limit: int = 50,
    role: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[User]:
    safe_limit = max(1, min(limit, 200))
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    query = query.order_by(User.created_at.desc()).limit(safe_limit)
    return list(db.scalars(query).all())


@router.patch("/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> User:
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target_user.id == current_user.id and payload.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A super admin cannot demote their own account")

    previous_role = target_user.role
    target_user.role = payload.role
    audit_user_decision(db, current_user, target_user, "user.role_updated", payload.reason, previous_role, payload.role)
    db.commit()
    db.refresh(target_user)
    return target_user


@router.patch("/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> User:
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target_user.id == current_user.id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A super admin cannot deactivate their own account")

    previous_status = target_user.is_active
    target_user.is_active = payload.is_active
    audit_user_decision(db, current_user, target_user, "user.status_updated", payload.reason, previous_status, payload.is_active)
    db.commit()
    db.refresh(target_user)
    return target_user

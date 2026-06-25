from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_user import User
from app.schemas import InstitutionalUserCreate, UserPasswordReset, UserRead, UserRoleUpdate, UserStatusUpdate
from app.security import get_password_hash

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


@router.get("", response_model=dict)
def list_users(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=100),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.email.ilike(term),
                User.full_name.ilike(term),
            )
        )
    query = query.order_by(User.created_at.desc())
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    raw_items = list(db.scalars(query.offset(offset).limit(limit)).all())
    items = [UserRead.model_validate(u) for u in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_institutional_user(
    payload: InstitutionalUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> User:
    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=get_password_hash(payload.initial_password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="user.created",
            entity="user",
            entity_id=user.id,
            details={
                "email": user.email,
                "role": user.role,
                "reason": payload.reason,
                "created_by": current_user.email,
            },
        )
    )
    db.commit()
    db.refresh(user)
    return user


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


@router.post("/{user_id}/reset-password", response_model=UserRead)
def reset_user_password(
    user_id: str,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> User:
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target_user.password_hash = get_password_hash(payload.new_password)
    audit_user_decision(db, current_user, target_user, "user.password_reset", payload.reason, "set", "reset")
    db.commit()
    db.refresh(target_user)
    return target_user

@router.patch("/{user_id}/center", response_model=UserRead)
def assign_user_center(
    user_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> User:
    """
    Assigne (ou retire) un agent 'center' à un centre.
    Payload : {"center_id": "<uuid>" | null}
    Seuls les users de role 'center' peuvent être associés à un centre.
    """
    from app.models_center import Center

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target.role not in ("center",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Seuls les agents 'center' peuvent être associés à un centre (rôle actuel: {target.role})",
        )

    new_center_id = payload.get("center_id")
    if new_center_id and not db.get(Center, new_center_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre introuvable")

    old_center_id = getattr(target, "center_id", None)
    target.center_id = new_center_id  # type: ignore[assignment]

    from app.models_audit import AuditLog
    db.add(AuditLog(
        actor_id=current_user.id,
        action="user.center_assigned",
        entity="user",
        entity_id=user_id,
        details={
            "old_center_id": old_center_id,
            "new_center_id": new_center_id,
            "user_email": target.email,
        },
    ))
    db.commit()
    db.refresh(target)
    return target

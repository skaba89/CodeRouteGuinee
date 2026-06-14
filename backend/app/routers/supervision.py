from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_user import User
from app.schemas import AuditLogRead

router = APIRouter(prefix="/supervision", tags=["supervision"])


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    limit: int = 50,
    action: str | None = None,
    entity: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[AuditLog]:
    safe_limit = max(1, min(limit, 200))
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(safe_limit)
    if action:
        query = query.where(AuditLog.action == action)
    if entity:
        query = query.where(AuditLog.entity == entity)
    return list(db.scalars(query).all())

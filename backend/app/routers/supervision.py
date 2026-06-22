import csv
from io import StringIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_user import User
from app.schemas import AuditLogRead

router = APIRouter(prefix="/supervision", tags=["supervision"])


@router.get("/audit-logs", response_model=dict)
def list_audit_logs(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=100),
    action: str | None = None,
    entity: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[AuditLog]:
    safe_limit = max(1, min(limit, 200))
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if entity:
        query = query.where(AuditLog.entity == entity)
    query = query.order_by(AuditLog.created_at.desc()).limit(safe_limit)
    if search:
        query = query.where(
            AuditLog.action.ilike(f"%{search}%")
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    raw_items = list(db.scalars(query.offset(offset)).all())
    items = [AuditLogRead.model_validate(x) for x in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.get("/audit-logs/export.csv")
def export_audit_logs_csv(
    limit: int = 500,
    action: str | None = None,
    entity: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Response:
    safe_limit = max(1, min(limit, 5000))
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if entity:
        query = query.where(AuditLog.entity == entity)
    logs = db.scalars(query.order_by(AuditLog.created_at.desc()).limit(safe_limit)).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["created_at", "actor_id", "action", "entity", "entity_id", "details"])
    for log in logs:
        writer.writerow([
            log.created_at.isoformat(),
            log.actor_id or "",
            log.action,
            log.entity,
            log.entity_id or "",
            log.details or {},
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="coderoute-audit-logs.csv"'},
    )

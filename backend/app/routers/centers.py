from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_user import User
from app.schemas import CenterCreate, CenterOfficialImportRequest, CenterOfficialImportResult, CenterRead, CenterStatusUpdate

router = APIRouter(prefix="/centers", tags=["centers"])


@router.get("", response_model=dict)
def list_centers(
    limit: int = Query(default=20, ge=1, le=200),  # 135 centres nationaux en une requête
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=100),
    status_filter: str | None = Query(default=None, alias="status"),
    prefecture: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center", "candidate")),
) -> list[Center]:
    q = select(Center).order_by(Center.name.asc())
    if search:
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                Center.name.ilike(term),
                Center.code.ilike(term),
                Center.city.ilike(term),
                Center.commune.ilike(term),
            )
        )
    if status_filter:
        q = q.where(Center.status == status_filter)
    if prefecture:
        q = q.where(Center.prefecture.ilike(f"%{prefecture}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    raw_items = list(db.scalars(q.offset(offset).limit(limit)).all())
    items = [CenterRead.model_validate(x) for x in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.post("", response_model=CenterRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin", "super_admin"))])
def create_center(payload: CenterCreate, db: Session = Depends(get_db)) -> Center:
    center = Center(**payload.model_dump())
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


@router.post("/import-official", response_model=CenterOfficialImportResult)
def import_official_centers(
    payload: CenterOfficialImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CenterOfficialImportResult:
    normalized_codes = [row.code.strip().upper() for row in payload.centers]
    duplicate_codes = sorted({code for code in normalized_codes if normalized_codes.count(code) > 1})
    if duplicate_codes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Duplicate center codes in import payload", "codes": duplicate_codes},
        )

    existing_centers = {
        center.code: center
        for center in db.scalars(select(Center).where(Center.code.in_(normalized_codes))).all()
    }
    if payload.dry_run:
        existing_codes = [code for code in normalized_codes if code in existing_centers]
        return CenterOfficialImportResult(
            dry_run=True,
            imported=len(normalized_codes),
            created=len(normalized_codes) - len(existing_codes),
            updated=len(existing_codes),
            skipped=0,
            codes=normalized_codes,
        )

    created = 0
    updated = 0
    imported_codes: list[str] = []

    for row in payload.centers:
        code = row.code.strip().upper()
        center = existing_centers.get(code)
        if center is None:
            center = Center(code=code)
            created += 1
        else:
            updated += 1
        center.name = row.name.strip()
        center.city = row.city.strip()
        center.address = row.address.strip()
        center.capacity = row.capacity
        center.status = row.status
        db.add(center)
        imported_codes.append(code)

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="center.official_import",
            entity="center",
            entity_id="official-import",
            details={
                "source": payload.source,
                "reason": payload.reason,
                "imported": len(imported_codes),
                "created": created,
                "updated": updated,
                "codes": imported_codes[:50],
            },
        )
    )
    db.commit()
    return CenterOfficialImportResult(
        dry_run=False,
        imported=len(imported_codes),
        created=created,
        updated=updated,
        skipped=0,
        codes=imported_codes,
    )


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

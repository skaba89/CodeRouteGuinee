from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_user import User
from app.schemas import CenterCreate, CenterOfficialImportRequest, CenterOfficialImportResult, CenterRead, CenterStatusUpdate

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

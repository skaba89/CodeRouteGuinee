from datetime import datetime
from app.time_utils import utc_now

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_center_station import CenterStation
from app.models_user import User

router = APIRouter(prefix="/center-stations", tags=["center-stations"])

ALLOWED_STATUSES = {"active", "disabled", "maintenance"}


class CenterStationCreate(BaseModel):
    center_id: str
    device_key: str = Field(min_length=4)
    label: str = Field(min_length=2)
    room: str | None = None
    status: str = "active"


class CenterStationUpdate(BaseModel):
    label: str | None = None
    room: str | None = None
    status: str | None = None


class CenterStationRead(BaseModel):
    id: str
    center_id: str
    device_key: str
    label: str
    status: str
    room: str | None = None
    created_by_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def normalize_status(value: str) -> str:
    normalized = value.lower().strip()
    if normalized not in ALLOWED_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid station status")
    return normalized


@router.post("", response_model=CenterStationRead, status_code=status.HTTP_201_CREATED)
def create_center_station(
    payload: CenterStationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CenterStation:
    center = db.get(Center, payload.center_id)
    if not center:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Center not found")

    existing = db.scalar(
        select(CenterStation).where(
            CenterStation.center_id == center.id,
            CenterStation.device_key == payload.device_key,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Station already exists for this center")

    station = CenterStation(
        center_id=center.id,
        device_key=payload.device_key,
        label=payload.label,
        room=payload.room,
        status=normalize_status(payload.status),
        created_by_id=current_user.id,
    )
    db.add(station)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="center_station.created",
            entity="center_station",
            entity_id=station.id,
            details={"center_id": center.id, "center_code": center.code, "device_key": station.device_key},
        )
    )
    db.commit()
    db.refresh(station)
    return station


@router.get("", response_model=list[CenterStationRead])
def list_center_stations(
    center_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[CenterStation]:
    query = select(CenterStation)
    if center_id:
        query = query.where(CenterStation.center_id == center_id)
    if status_filter:
        query = query.where(CenterStation.status == normalize_status(status_filter))
    query = query.order_by(CenterStation.created_at.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(query).all())


@router.patch("/{station_id}", response_model=CenterStationRead)
def update_center_station(
    station_id: str,
    payload: CenterStationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CenterStation:
    station = db.get(CenterStation, station_id)
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Station not found")

    previous_status = station.status
    if payload.label is not None:
        station.label = payload.label
    if payload.room is not None:
        station.room = payload.room
    if payload.status is not None:
        station.status = normalize_status(payload.status)
    station.updated_at = utc_now()

    db.add(station)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="center_station.updated",
            entity="center_station",
            entity_id=station.id,
            details={
                "center_id": station.center_id,
                "device_key": station.device_key,
                "previous_status": previous_status,
                "new_status": station.status,
            },
        )
    )
    db.commit()
    db.refresh(station)
    return station

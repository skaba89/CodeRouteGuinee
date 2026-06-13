from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models_center import Center
from app.schemas import CenterCreate, CenterRead

router = APIRouter(prefix="/centers", tags=["centers"])


@router.get("", response_model=list[CenterRead])
def list_centers(db: Session = Depends(get_db)) -> list[Center]:
    return list(db.scalars(select(Center).order_by(Center.created_at.desc())).all())


@router.post("", response_model=CenterRead, status_code=status.HTTP_201_CREATED)
def create_center(payload: CenterCreate, db: Session = Depends(get_db)) -> Center:
    center = Center(**payload.model_dump())
    db.add(center)
    db.commit()
    db.refresh(center)
    return center

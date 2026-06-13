from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models_candidate import Candidate
from app.schemas import CandidateCreate, CandidateRead

router = APIRouter(prefix="/candidates", tags=["candidates"])


def build_candidate_reference(db: Session) -> str:
    count = db.query(Candidate).count() + 1
    return f"GN-CODE-{datetime.utcnow().year}-{count:06d}"


@router.get("", response_model=list[CandidateRead])
def list_candidates(db: Session = Depends(get_db)) -> list[Candidate]:
    return list(db.scalars(select(Candidate).order_by(Candidate.created_at.desc())).all())


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)) -> Candidate:
    candidate = Candidate(reference=build_candidate_reference(db), **payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate

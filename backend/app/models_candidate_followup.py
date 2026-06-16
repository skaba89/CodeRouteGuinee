import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class CandidateFollowup(Base):
    __tablename__ = "candidate_followups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("exam_attempts.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(60), default="review", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="submitted", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    handled_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

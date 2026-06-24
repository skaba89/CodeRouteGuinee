import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id:           Mapped[str]        = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str]        = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    session_id:   Mapped[str]        = mapped_column(ForeignKey("exam_sessions.id"), nullable=False, index=True)
    status:       Mapped[str]        = mapped_column(String(50), default="started", nullable=False, index=True)
    answers:      Mapped[dict | None] = mapped_column(JSON, nullable=True)
    score:        Mapped[int | None]  = mapped_column(Integer, nullable=True)
    passed:       Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    started_at:   Mapped[datetime]    = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

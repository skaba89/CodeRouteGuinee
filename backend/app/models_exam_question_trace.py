import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class ExamQuestionTrace(Base):
    __tablename__ = "exam_question_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("exam_attempts.id"), nullable=False, index=True)
    question_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bank_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(80), nullable=False)
    selection_mode: Mapped[str] = mapped_column(String(80), default="active_bank_snapshot", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

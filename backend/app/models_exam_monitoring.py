from datetime import datetime
import uuid
from app.time_utils import utc_now

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class ExamMonitoringEvent(Base):
    __tablename__ = "exam_monitoring_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    center_id: Mapped[str | None] = mapped_column(ForeignKey("centers.id"), nullable=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("exam_sessions.id"), nullable=False)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("exam_attempts.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(30), default="low", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reported_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

from datetime import datetime
import uuid
from app.time_utils import utc_now

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class CenterIncident(Base):
    __tablename__ = "center_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    center_id: Mapped[str] = mapped_column(ForeignKey("centers.id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("exam_sessions.id"), nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("exam_attempts.id"), nullable=True)
    incident_type: Mapped[str] = mapped_column(String(80), default="technical_issue", nullable=False)
    severity: Mapped[str] = mapped_column(String(30), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    new_attempt_id: Mapped[str | None] = mapped_column(ForeignKey("exam_attempts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

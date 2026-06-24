import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("exam_sessions.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="confirmed", nullable=False, index=True)
    verification_code: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    notes:              Mapped[str | None]      = mapped_column(Text, nullable=True)
    cancelled_at:       Mapped[datetime | None]  = mapped_column(DateTime, nullable=True)
    payment_reference:  Mapped[str | None]       = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)

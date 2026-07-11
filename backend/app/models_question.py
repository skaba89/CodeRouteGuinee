import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_alt: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Workflow de validation officielle (certification DNTT) ────────────
    # draft     : en cours de rédaction, jamais tirée à l'examen
    # submitted : soumise pour validation par la DNTT
    # approved  : validée officiellement — seule éligible à l'examen réel
    # rejected  : refusée (avec motif), à corriger
    validation_status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False, index=True,
    )
    validated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Candidate(Base):
    __tablename__ = "candidates"

    id:              Mapped[str]        = mapped_column(String(36), primary_key=True, default=new_id)
    reference:       Mapped[str]        = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name:      Mapped[str]        = mapped_column(String(120), nullable=False)
    last_name:       Mapped[str]        = mapped_column(String(120), nullable=False)
    identity_number: Mapped[str]        = mapped_column(String(120), index=True, nullable=False)
    phone:           Mapped[str]        = mapped_column(String(50), nullable=False)
    email:           Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    permit_category: Mapped[str]        = mapped_column(String(10), default="B", nullable=False)
    status:          Mapped[str]        = mapped_column(String(50), default="registered", nullable=False)

    # Champs ajoutés — migration 0006
    city:            Mapped[str | None]  = mapped_column(String(100), nullable=True)
    date_of_birth:   Mapped[date | None] = mapped_column(Date, nullable=True)
    address:         Mapped[str | None]  = mapped_column(Text, nullable=True)
    attempt_count:   Mapped[int]         = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )

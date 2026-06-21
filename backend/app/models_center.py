"""
Modèle Centre d'examen CodeRoute Guinée.

Règles métier DNTT :
  - Capacité max par session : 35 candidats
  - Sessions max par semaine : 3
  - Minimum 3 centres par commune
  - Chaque centre doit être agréé par la DNTT
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Center(Base):
    __tablename__ = "centers"
    __table_args__ = (
        CheckConstraint(
            "max_sessions_per_week >= 1 AND max_sessions_per_week <= 7",
            name="ck_centers_max_sessions_per_week",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    commune: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prefecture: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=35, nullable=False)
    max_sessions_per_week: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending_audit", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )

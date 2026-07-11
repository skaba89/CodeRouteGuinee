import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)

    # ── Chaînage cryptographique (journal inviolable / tamper-evident) ──────
    # seq        : numéro de séquence strictement croissant (ordre inaltérable)
    # entry_hash : SHA-256 du contenu de CETTE entrée + prev_hash
    # prev_hash  : entry_hash de l'entrée précédente (chaîne)
    # Altérer/supprimer une entrée passée casse la chaîne → détectable.
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

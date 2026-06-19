from datetime import datetime
import uuid
from app.time_utils import utc_now

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class InstitutionalAuthorization(Base):
    __tablename__ = "institutional_authorizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    authority: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False, index=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

from datetime import datetime
import uuid
from app.time_utils import utc_now

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class CenterStation(Base):
    __tablename__ = "center_stations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    center_id: Mapped[str] = mapped_column(ForeignKey("centers.id"), nullable=False, index=True)
    device_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    room: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

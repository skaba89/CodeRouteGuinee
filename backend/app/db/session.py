from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from app import (  # noqa: F401
        models_audit,
        models_booking,
        models_candidate,
        models_candidate_identity,
        models_center,
        models_center_incident,
        models_device_session,
        models_exam_attempt,
        models_exam_monitoring,
        models_exam_review,
        models_payment,
        models_question,
        models_session,
        models_user,
    )

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

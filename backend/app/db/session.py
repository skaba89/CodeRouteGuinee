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
    if not settings.auto_create_tables:
        return
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Migrations SQLite pour les nouvelles colonnes — compatibilité tests
    # (en production PostgreSQL utilise Alembic, mais les tests utilisent SQLite in-memory)
    if settings.database_url.startswith("sqlite"):
        _sqlite_add_columns_if_missing()


def _sqlite_add_columns_if_missing() -> None:
    """Ajoute les colonnes manquantes dans SQLite (tests uniquement)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    migrations = [
        # (table, colonne, type SQL)
        ("centers", "commune", "VARCHAR(120)"),
        ("centers", "prefecture", "VARCHAR(120)"),
        ("centers", "latitude", "FLOAT"),
        ("centers", "longitude", "FLOAT"),
        ("centers", "max_sessions_per_week", "INTEGER DEFAULT 3 NOT NULL"),
        ("exam_sessions", "capacity", None),  # déjà existante, juste vérif
    ]
    with engine.connect() as conn:
        for table, col, col_type in migrations:
            if col_type is None:
                continue
            try:
                existing_cols = [c["name"] for c in inspector.get_columns(table)]
                if col not in existing_cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    conn.commit()
            except Exception:
                pass  # Colonne déjà présente ou table inexistante


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

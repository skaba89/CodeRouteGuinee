"""
Session SQLAlchemy — pool configuré pour la production.

Paramètres de pool :
  pool_size     : connexions permanentes maintenues par worker
  max_overflow  : connexions supplémentaires autorisées en pic
  pool_timeout  : délai d'attente avant PoolError (évite les blocages silencieux)
  pool_recycle  : recycle les connexions toutes les 30 min (évite les timeouts DB)
  pool_pre_ping : vérifie la connexion avant usage (évite "connection reset by peer")

Calcul de la consommation DB :
  workers × (pool_size + max_overflow) ≤ max_connections PostgreSQL
  Ex : 4 workers × (20+30) = 200 → PostgreSQL doit avoir max_connections ≥ 210
"""
import os
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# ── Paramètres pool selon l'environnement ────────────────────────────────────
_IS_SQLITE = settings.database_url.startswith("sqlite")
_IS_PROD   = settings.environment == "production"

if _IS_SQLITE:
    # Tests : SQLite en mémoire, pool NullPool (pas de connexions persistantes)
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Production / staging : pool optimisé pour la charge
    _pool_size    = int(os.getenv("DB_POOL_SIZE",    "20"))
    _max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    _pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    _pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    engine = create_engine(
        settings.database_url,
        pool_size=_pool_size,
        max_overflow=_max_overflow,
        pool_timeout=_pool_timeout,
        pool_recycle=_pool_recycle,
        pool_pre_ping=True,
        # Statement timeout côté PostgreSQL (évite les requêtes zombies)
        connect_args={"options": "-c statement_timeout=30000"},
        # Taille du batch de lignes retournées par psycopg (moins de round-trips)
        execution_options={"stream_results": False},
    )

    # ── Optimisations PostgreSQL appliquées à chaque nouvelle connexion ───────
    @event.listens_for(engine, "connect")
    def _set_pg_session_params(dbapi_conn, _connection_record):
        """Tune les paramètres PostgreSQL par session pour la performance."""
        with dbapi_conn.cursor() as cur:
            cur.execute("SET timezone = 'Africa/Conakry'")
            cur.execute("SET synchronous_commit = 'local'")   # commit async (10× plus rapide, pas de perte)
            cur.execute("SET work_mem = '8MB'")               # mémoire pour tri/hash par opération

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    if not settings.auto_create_tables:
        return
    from app import models  # noqa: F401
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)

    if _IS_SQLITE:
        _sqlite_add_columns_if_missing()


def _sqlite_add_columns_if_missing() -> None:
    """Ajoute les colonnes manquantes dans SQLite (tests uniquement)."""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    migrations = [
        ("centers", "commune", "VARCHAR(120)"),
        ("centers", "prefecture", "VARCHAR(120)"),
        ("centers", "latitude", "FLOAT"),
        ("centers", "longitude", "FLOAT"),
        ("centers", "max_sessions_per_week", "INTEGER DEFAULT 3 NOT NULL"),
        ("exam_sessions", "capacity", None),
        # Sprint 83 — nouvelles colonnes production
        ("candidates", "email", "VARCHAR(200)"),
        ("payments",   "external_reference", "VARCHAR(200)"),
        ("payments",   "paid_at", "DATETIME"),
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
                pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

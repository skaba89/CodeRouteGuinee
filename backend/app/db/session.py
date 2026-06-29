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

    # Neon serverless : utiliser NullPool + connexion poolée (-pooler dans l'URL)
    # afin de laisser PgBouncer gérer le pool (10 000 connexions client max).
    # Sur Postgres classique : QueuePool avec pool_size/max_overflow.
    _use_neon_pooler = "neon.tech" in settings.database_url and "-pooler" in settings.database_url
    _use_neon_direct = "neon.tech" in settings.database_url and "-pooler" not in settings.database_url

    if _use_neon_pooler:
        # Connexion poolée Neon → NullPool (pas de pool côté app, PgBouncer gère tout)
        from sqlalchemy.pool import NullPool
        engine = create_engine(
            settings.database_url,
            poolclass=NullPool,
            connect_args={"options": "-c statement_timeout=30000"},
        )
    elif _use_neon_direct:
        # Connexion directe Neon (migrations Alembic) → pool minimal + pre_ping
        engine = create_engine(
            settings.database_url,
            pool_size=2,
            max_overflow=3,
            pool_timeout=_pool_timeout,
            pool_recycle=300,   # 5 min = durée auto-suspend Neon par défaut
            pool_pre_ping=True,
            connect_args={"options": "-c statement_timeout=30000"},
        )
    else:
        # PostgreSQL classique (dev local, docker-compose)
        engine = create_engine(
            settings.database_url,
            pool_size=_pool_size,
            max_overflow=_max_overflow,
            pool_timeout=_pool_timeout,
            pool_recycle=_pool_recycle,
            pool_pre_ping=True,
            connect_args={"options": "-c statement_timeout=30000"},
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
    """Initialise la base de données.

    En production (AUTO_CREATE_TABLES=false), cette fonction ne fait rien.
    Les migrations sont gérées par Alembic (entrypoint.sh : alembic upgrade head).
    En développement local avec SQLite, crée les tables automatiquement.
    """
    if not settings.auto_create_tables:
        return  # Production : Alembic gère le schéma, on ne touche pas à la DB ici
    try:
        from app import models  # noqa: F401
        from app.db.base import Base
        Base.metadata.create_all(bind=engine)
        if _IS_SQLITE:
            _sqlite_add_columns_if_missing()
    except Exception as e:
        import logging
        logging.getLogger("app.db").warning(
            "init_db create_all failed (non-blocking): %s — "
            "En production, définir AUTO_CREATE_TABLES=false et utiliser Alembic.",
            e,
        )


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
        ("bookings",   "notes", "TEXT"),
        ("bookings",   "cancelled_at", "DATETIME"),
        ("bookings",   "payment_reference", "VARCHAR(80)"),
        ("candidates", "city", "VARCHAR(100)"),
        ("candidates", "date_of_birth", "DATE"),
        ("candidates", "address", "TEXT"),
        ("candidates", "attempt_count", "INTEGER DEFAULT 0 NOT NULL"),
        ("users",      "center_id",    "VARCHAR(36)"),
    ]
    # Liste blanche explicite pour prévenir toute injection SQL
    # (même si les valeurs sont hardcodées, on valide explicitement)
    _ALLOWED_TABLES = {
        "centers", "exam_sessions", "candidates", "payments",
        "bookings", "questions", "exam_attempts", "device_sessions", "users",
        "exam_monitoring_events", "exam_question_traces", "center_incidents",
    }
    _SAFE_COL_PATTERN = __import__("re").compile(r"^[a-z_][a-z0-9_]{0,63}$")

    with engine.connect() as conn:
        for table, col, col_type in migrations:
            if col_type is None:
                continue
            # Validation liste blanche
            if table not in _ALLOWED_TABLES:
                import logging as _log
                _log.getLogger("coderoute.db").warning(
                    "ALTER TABLE refusé — table non autorisée : %s", table
                )
                continue
            if not _SAFE_COL_PATTERN.match(col):
                import logging as _log
                _log.getLogger("coderoute.db").warning(
                    "ALTER TABLE refusé — colonne invalide : %s", col
                )
                continue
            try:
                existing_cols = [c["name"] for c in inspector.get_columns(table)]
                if col not in existing_cols:
                    # Utiliser un dictionnaire pour le type (pas d'interpolation du type)
                    _SAFE_TYPES = {
                        "VARCHAR(120)", "VARCHAR(200)", "VARCHAR(100)", "VARCHAR(80)", "FLOAT", "INTEGER", "DATE",
                        "INTEGER DEFAULT 3 NOT NULL", "DATETIME", "BOOLEAN",
                    }
                    safe_type = col_type if col_type in _SAFE_TYPES else None
                    if safe_type is None:
                        continue
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {safe_type}"))  # noqa: S608
                    conn.commit()
            except Exception:
                pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

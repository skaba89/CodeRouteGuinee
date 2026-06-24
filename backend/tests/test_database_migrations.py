from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app import models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base


def test_metadata_registers_all_production_tables() -> None:
    expected_tables = {
        "audit_logs",
        "bookings",
        "candidate_followups",
        "candidate_identity_checks",
        "candidates",
        "center_incidents",
        "center_stations",
        "centers",
        "device_sessions",
        "exam_attempts",
        "exam_monitoring_events",
        "exam_question_traces",
        "exam_review_decisions",
        "exam_sessions",
        "institutional_authorizations",
        "payments",
        "question_governance_decisions",
        "questions",
        "users",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))


def test_alembic_initial_migration_is_available() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    assert (backend_root / "alembic.ini").exists()
    assert (backend_root / "alembic" / "env.py").exists()
    assert (backend_root / "alembic" / "versions" / "20260617_0001_initial_schema.py").exists()
    assert (backend_root / "alembic" / "versions" / "20260618_0002_question_media_fields.py").exists()
    assert (backend_root / "alembic" / "versions" / "20260619_0003_explicit_ddl_and_rate_limit_table.py").exists()
    assert (backend_root / "alembic" / "versions" / "20260620_0004_session_capacity_rules.py").exists()
    assert (backend_root / "alembic" / "versions" / "20260623_0005_payment_external_reference.py").exists()


def test_question_metadata_includes_multimedia_fields() -> None:
    question_columns = set(Base.metadata.tables["questions"].columns.keys())
    assert {"media_type", "media_url", "media_alt"}.issubset(question_columns)


def test_alembic_upgrade_head_from_empty_sqlite_database(tmp_path, monkeypatch) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "coderoute-empty.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    try:
        tables = set(inspector.get_table_names())
        assert set(Base.metadata.tables).issubset(tables)
        question_columns = {column["name"] for column in inspector.get_columns("questions")}
        assert {"media_type", "media_url", "media_alt"}.issubset(question_columns)
        with engine.connect() as connection:
            version_rows = connection.exec_driver_sql("SELECT version_num FROM alembic_version").fetchall()
        assert version_rows == [("0006",)]
    finally:
        engine.dispose()
        get_settings.cache_clear()

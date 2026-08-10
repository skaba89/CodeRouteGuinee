from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
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
        "media_assets",
        "payments",
        "question_governance_decisions",
        "question_media",
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
    assert (backend_root / "alembic" / "versions" / "20260810_0015_media_asset_architecture.py").exists()


def test_question_metadata_includes_multimedia_fields() -> None:
    question_columns = set(Base.metadata.tables["questions"].columns.keys())
    assert {"media_type", "media_url", "media_alt"}.issubset(question_columns)


def test_media_metadata_is_additive_and_normalized() -> None:
    media_columns = set(Base.metadata.tables["media_assets"].columns.keys())
    assert {
        "id",
        "uuid",
        "media_type",
        "usage_type",
        "storage_provider",
        "storage_key",
        "public_url",
        "secure_url",
        "mime_type",
        "width",
        "height",
        "duration_seconds",
        "file_size_bytes",
        "checksum_sha256",
        "poster_media_id",
        "fallback_media_id",
        "theme",
        "subtheme",
        "country_code",
        "regulatory_scope",
        "source_type",
        "source_reference",
        "license_type",
        "license_reference",
        "license_expiration_date",
        "copyright_owner",
        "quality_status",
        "regulatory_status",
        "regulatory_authority_reference",
        "validated_by",
        "validated_at",
        "created_by",
        "created_at",
        "updated_at",
        "archived_at",
    }.issubset(media_columns)

    link_columns = set(Base.metadata.tables["question_media"].columns.keys())
    assert {"id", "question_id", "media_id", "role", "display_order", "created_at"}.issubset(link_columns)

    # Legacy fields deliberately remain during the migration window.
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
        assert {"media_assets", "question_media"}.issubset(tables)

        question_columns = {column["name"] for column in inspector.get_columns("questions")}
        assert {"media_type", "media_url", "media_alt"}.issubset(question_columns)

        media_columns = {column["name"] for column in inspector.get_columns("media_assets")}
        assert {"checksum_sha256", "quality_status", "regulatory_status", "poster_media_id", "fallback_media_id"}.issubset(media_columns)

        question_media_columns = {column["name"] for column in inspector.get_columns("question_media")}
        assert {"question_id", "media_id", "role", "display_order"}.issubset(question_media_columns)

        with engine.connect() as connection:
            version_rows = connection.exec_driver_sql("SELECT version_num FROM alembic_version").fetchall()
        assert version_rows == [("0015",)]
    finally:
        engine.dispose()
        get_settings.cache_clear()

from pathlib import Path

from app import models  # noqa: F401
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


def test_question_metadata_includes_multimedia_fields() -> None:
    question_columns = set(Base.metadata.tables["questions"].columns.keys())
    assert {"media_type", "media_url", "media_alt"}.issubset(question_columns)

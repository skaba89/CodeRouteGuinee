from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.db.session import SessionLocal, init_db
from app.models_audit import AuditLog
from app.reliability_metrics import latest_reliability_evidence_times


def test_delayed_ingestion_does_not_make_old_backup_look_fresh() -> None:
    init_db()
    now = datetime.now(UTC).replace(tzinfo=None)
    old_occurrence = datetime(2026, 8, 1, 1, 30, tzinfo=UTC)
    newer_occurrence = datetime(2026, 8, 8, 1, 30, tzinfo=UTC)

    db = SessionLocal()
    try:
        db.execute(delete(AuditLog).where(AuditLog.action == "reliability.backup_uploaded"))
        db.add(AuditLog(
            actor_id=None,
            action="reliability.backup_uploaded",
            entity="reliability",
            details={"occurred_at": newer_occurrence.isoformat()},
            created_at=now - timedelta(days=1),
        ))
        # Cette preuve est ingérée plus tard, mais concerne en réalité un vieux backup.
        db.add(AuditLog(
            actor_id=None,
            action="reliability.backup_uploaded",
            entity="reliability",
            details={"occurred_at": old_occurrence.isoformat()},
            created_at=now,
        ))
        db.commit()

        times = latest_reliability_evidence_times(db)
        assert times["backup_uploaded"] == newer_occurrence
    finally:
        db.close()

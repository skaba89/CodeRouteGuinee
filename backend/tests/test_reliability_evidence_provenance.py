from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.db.session import SessionLocal, init_db
from app.models_audit import AuditLog
from app.reliability_metrics import latest_reliability_evidence, latest_reliability_evidence_times
from app.routers.reliability import reliability_status

ACTIONS = (
    "reliability.backup_uploaded",
    "reliability.restore_drill_passed",
    "reliability.ha_failover_probe_passed",
    "reliability.pitr_drill_passed",
)


def _reset(db) -> None:
    db.execute(delete(AuditLog).where(AuditLog.action.in_(ACTIONS)))
    db.commit()


def test_latest_evidence_uses_occurred_at_and_exposes_only_allowlisted_fields() -> None:
    init_db()
    now = datetime.now(UTC)
    with SessionLocal() as db:
        _reset(db)
        # Ingest the genuinely newer evidence first, then a late-arriving old event.
        db.add(
            AuditLog(
                actor_id=None,
                action="reliability.backup_uploaded",
                entity="reliability",
                details={
                    "kind": "backup_uploaded",
                    "occurred_at": (now - timedelta(minutes=5)).isoformat(),
                    "artifact_sha256": "a" * 64,
                    "region": "paris",
                    "reference": "BACKUP-2026-08-09-001",
                    "password": "must-never-leak",
                    "arbitrary": "must-never-leak",
                },
            )
        )
        db.commit()
        db.add(
            AuditLog(
                actor_id=None,
                action="reliability.backup_uploaded",
                entity="reliability",
                details={
                    "kind": "backup_uploaded",
                    "occurred_at": (now - timedelta(days=2)).isoformat(),
                    "artifact_sha256": "b" * 64,
                    "region": "paris",
                    "reference": "BACKUP-OLD-LATE-INGESTION",
                },
            )
        )
        db.commit()

        evidence = latest_reliability_evidence(db)
        backup = evidence["backup_uploaded"]
        assert backup is not None
        assert backup["artifact_sha256"] == "a" * 64
        assert backup["reference"] == "BACKUP-2026-08-09-001"
        assert backup["region"] == "paris"
        assert set(backup) == {
            "kind",
            "occurred_at",
            "artifact_sha256",
            "region",
            "reference",
            "availability_percent",
            "duration_seconds",
            "observed_rpo_minutes",
            "observed_rto_minutes",
        }
        assert "password" not in backup
        assert "arbitrary" not in backup

        times = latest_reliability_evidence_times(db)
        assert times["backup_uploaded"] is not None
        assert abs((times["backup_uploaded"] - (now - timedelta(minutes=5))).total_seconds()) < 1


def test_pitr_provenance_keeps_hash_reference_and_measured_rpo_rto() -> None:
    init_db()
    occurred = datetime.now(UTC) - timedelta(minutes=1)
    with SessionLocal() as db:
        _reset(db)
        db.add(
            AuditLog(
                actor_id=None,
                action="reliability.pitr_drill_passed",
                entity="reliability",
                details={
                    "kind": "pitr_drill_passed",
                    "occurred_at": occurred.isoformat(),
                    "artifact_sha256": "f" * 64,
                    "reference": "PITR-DRILL-2026-08-09",
                    "observed_rpo_minutes": 3.5,
                    "observed_rto_minutes": 18.0,
                    "authorization": "Bearer should-never-leak",
                },
            )
        )
        db.commit()

        pitr = latest_reliability_evidence(db)["pitr_drill_passed"]
        assert pitr is not None
        assert pitr["artifact_sha256"] == "f" * 64
        assert pitr["reference"] == "PITR-DRILL-2026-08-09"
        assert pitr["observed_rpo_minutes"] == 3.5
        assert pitr["observed_rto_minutes"] == 18.0
        assert "authorization" not in pitr


def test_unsafe_legacy_reference_is_suppressed_not_returned() -> None:
    init_db()
    with SessionLocal() as db:
        _reset(db)
        db.add(
            AuditLog(
                actor_id=None,
                action="reliability.restore_drill_passed",
                entity="reliability",
                details={
                    "kind": "restore_drill_passed",
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "artifact_sha256": "c" * 64,
                    "reference": "https://user:secret@example.org/receipt",
                },
            )
        )
        db.commit()
        restore = latest_reliability_evidence(db)["restore_drill_passed"]
        assert restore is not None
        assert restore["artifact_sha256"] == "c" * 64
        assert restore["reference"] is None


def test_reliability_status_returns_safe_details_and_legacy_timestamp_view() -> None:
    init_db()
    occurred = datetime.now(UTC) - timedelta(minutes=2)
    with SessionLocal() as db:
        _reset(db)
        db.add(
            AuditLog(
                actor_id=None,
                action="reliability.ha_failover_probe_passed",
                entity="reliability",
                details={
                    "kind": "ha_failover_probe_passed",
                    "occurred_at": occurred.isoformat(),
                    "availability_percent": 100.0,
                    "duration_seconds": 120.0,
                },
            )
        )
        db.commit()

        body = reliability_status(db=db, _current_user=None)  # dependency is irrelevant for direct unit call
        assert body["last_evidence"]["ha_failover_probe_passed"] is not None
        detail = body["last_evidence_details"]["ha_failover_probe_passed"]
        assert detail["availability_percent"] == 100.0
        assert detail["duration_seconds"] == 120.0
        assert detail["artifact_sha256"] is None

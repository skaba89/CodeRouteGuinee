from datetime import UTC, datetime

from sqlalchemy import delete

from app.db.session import SessionLocal, init_db
from app.models_audit import AuditLog
from app.national_governance import build_readiness


def _check(readiness: dict, code: str) -> dict:
    return next(item for item in readiness["checks"] if item["code"] == code)


def test_national_readiness_blocks_without_recent_pitr_evidence() -> None:
    init_db()
    with SessionLocal() as db:
        db.execute(delete(AuditLog).where(AuditLog.action == "reliability.pitr_drill_passed"))
        db.commit()

        readiness = build_readiness(db)
        pitr = _check(readiness, "pitr_provider")
        assert pitr["required"] is True
        assert pitr["status"] == "fail"
        assert pitr["evidence"]["last_success"] is None
        assert "pitr_provider" in readiness["blockers"]


def test_national_readiness_accepts_recent_successful_pitr_evidence() -> None:
    init_db()
    now = datetime.now(UTC)
    with SessionLocal() as db:
        db.execute(delete(AuditLog).where(AuditLog.action == "reliability.pitr_drill_passed"))
        db.add(
            AuditLog(
                actor_id=None,
                action="reliability.pitr_drill_passed",
                entity="reliability",
                details={
                    "occurred_at": now.isoformat(),
                    "reference": "PITR-DRILL-TEST",
                    "artifact_sha256": "a" * 64,
                    "observed_rpo_minutes": 2.0,
                    "observed_rto_minutes": 10.0,
                },
            )
        )
        db.commit()

        readiness = build_readiness(db)
        pitr = _check(readiness, "pitr_provider")
        assert pitr["status"] == "pass"
        assert pitr["evidence"]["last_success"] is not None
        assert "pitr_provider" not in readiness["blockers"]

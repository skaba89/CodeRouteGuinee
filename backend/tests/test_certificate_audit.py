from datetime import UTC, datetime

from app.models_audit import AuditLog
from app.routers.exams import _write_certificate_verification_log


class FakeDb:
    def __init__(self) -> None:
        self.items = []

    def add(self, item) -> None:
        self.items.append(item)


def test_certificate_verification_log_contains_context() -> None:
    now = datetime.now(UTC)
    db = FakeDb()

    _write_certificate_verification_log(
        db,
        attempt_id="attempt-1",
        valid=True,
        status_label="submitted",
        checked_at=now,
        extra_details={"candidate_reference": "GN-CODE-2026-000001"},
    )

    assert len(db.items) == 1
    audit_log = db.items[0]
    assert isinstance(audit_log, AuditLog)
    assert audit_log.action == "certificate.verify"
    assert audit_log.entity == "exam_certificate"
    assert audit_log.entity_id == "attempt-1"
    assert audit_log.details["valid"] is True
    assert audit_log.details["candidate_reference"] == "GN-CODE-2026-000001"

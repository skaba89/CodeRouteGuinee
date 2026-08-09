import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit_chain import ensure_audit_chain_anchor, verify_audit_chain
from app.db.base import Base
from app.models_audit import AuditLog
from app.soc_config import get_soc_settings


@pytest.fixture(autouse=True)
def _clear_soc_cache_after_test():
    yield
    get_soc_settings.cache_clear()


def _session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[AuditLog.__table__])
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _enable_chain(monkeypatch, key: str = "audit-hmac-test-key-" + ("x" * 40)) -> None:
    monkeypatch.setenv("SOC_ENABLED", "true")
    monkeypatch.setenv("SOC_PSEUDONYM_KEY", "soc-test-key-" + ("p" * 40))
    monkeypatch.setenv("AUDIT_CHAIN_ENABLED", "true")
    monkeypatch.setenv("AUDIT_CHAIN_HMAC_KEY", key)
    get_soc_settings.cache_clear()


def test_unchained_legacy_rows_are_anchored_then_new_rows_are_hmac(monkeypatch) -> None:
    _engine, Factory = _session_factory()
    monkeypatch.setenv("AUDIT_CHAIN_ENABLED", "false")
    get_soc_settings.cache_clear()
    with Factory() as db:
        db.add(AuditLog(action="legacy.one", entity="legacy", details={"v": 1}))
        db.add(AuditLog(action="legacy.two", entity="legacy", details={"v": 2}))
        db.commit()

    _enable_chain(monkeypatch)
    with Factory() as db:
        result = ensure_audit_chain_anchor(db)
        assert result["created"] is True
        db.add(AuditLog(action="security.test", entity="security", details={"ok": True}))
        db.commit()
        report = verify_audit_chain(db)
        assert report["valid"] is True
        assert report["legacy_entries"] == 2
        rows = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at)).all())
        legacy = [row for row in rows if row.action.startswith("legacy.")]
        assert all(row.seq is None and row.entry_hash is None for row in legacy)
        current = next(row for row in rows if row.action == "security.test")
        assert current.seq is not None
        assert current.entry_hash and len(current.entry_hash) == 64


def test_old_sha_chain_is_preserved_and_anchored_without_rewrite(monkeypatch) -> None:
    _engine, Factory = _session_factory()
    monkeypatch.setenv("AUDIT_CHAIN_ENABLED", "false")
    get_soc_settings.cache_clear()
    with Factory() as db:
        first = AuditLog(
            action="legacy.sha.one", entity="legacy", details={"v": 1},
            seq=1, prev_hash="0" * 64, entry_hash="1" * 64,
        )
        second = AuditLog(
            action="legacy.sha.two", entity="legacy", details={"v": 2},
            seq=2, prev_hash="1" * 64, entry_hash="2" * 64,
        )
        db.add_all([first, second])
        db.commit()
        first_id, second_id = first.id, second.id

    _enable_chain(monkeypatch)
    with Factory() as db:
        ensure_audit_chain_anchor(db)
        db.add(AuditLog(action="security.after-legacy", entity="security"))
        db.commit()
        report = verify_audit_chain(db)
        assert report["valid"] is True
        old_first, old_second = db.get(AuditLog, first_id), db.get(AuditLog, second_id)
        assert (old_first.seq, old_first.entry_hash) == (1, "1" * 64)
        assert (old_second.seq, old_second.entry_hash) == (2, "2" * 64)
        anchor = db.scalar(select(AuditLog).where(AuditLog.action == "audit.chain_anchor"))
        assert anchor.seq == 3
        assert anchor.prev_hash == "2" * 64


def test_direct_auditlog_add_is_automatically_chained(monkeypatch) -> None:
    _enable_chain(monkeypatch)
    _engine, Factory = _session_factory()
    with Factory() as db:
        ensure_audit_chain_anchor(db)
        entry = AuditLog(action="auth.login_failed", entity="auth", details={"email": "internal@example.gn"})
        db.add(entry)
        db.commit()
        assert entry.seq is not None
        assert entry.prev_hash
        assert entry.entry_hash and len(entry.entry_hash) == 64
        assert verify_audit_chain(db)["valid"] is True


def test_tampering_new_hmac_entry_is_detected(monkeypatch) -> None:
    _enable_chain(monkeypatch)
    engine, Factory = _session_factory()
    with Factory() as db:
        ensure_audit_chain_anchor(db)
        entry = AuditLog(action="security.original", entity="security", details={"value": 1})
        db.add(entry)
        db.commit()
        entry_id = entry.id

    with engine.begin() as conn:
        conn.execute(text("UPDATE audit_logs SET action='security.tampered' WHERE id=:id"), {"id": entry_id})
    with Factory() as db:
        report = verify_audit_chain(db)
        assert report["valid"] is False
        assert report["reason"] == "entry_hmac_mismatch"


def test_tampering_legacy_history_is_detected_by_anchor(monkeypatch) -> None:
    engine, Factory = _session_factory()
    monkeypatch.setenv("AUDIT_CHAIN_ENABLED", "false")
    get_soc_settings.cache_clear()
    with Factory() as db:
        legacy = AuditLog(action="legacy.original", entity="legacy", details={"value": 1})
        db.add(legacy)
        db.commit()
        legacy_id = legacy.id

    _enable_chain(monkeypatch)
    with Factory() as db:
        ensure_audit_chain_anchor(db)
        assert verify_audit_chain(db)["valid"] is True

    with engine.begin() as conn:
        conn.execute(text("UPDATE audit_logs SET action='legacy.tampered' WHERE id=:id"), {"id": legacy_id})
    with Factory() as db:
        report = verify_audit_chain(db)
        assert report["valid"] is False
        assert report["reason"] == "legacy_anchor_mismatch"


def test_second_anchor_call_is_idempotent(monkeypatch) -> None:
    _enable_chain(monkeypatch)
    _engine, Factory = _session_factory()
    with Factory() as db:
        first = ensure_audit_chain_anchor(db)
        second = ensure_audit_chain_anchor(db)
        assert first["created"] is True
        assert second["created"] is False
        anchors = list(db.scalars(select(AuditLog).where(AuditLog.action == "audit.chain_anchor")).all())
        assert len(anchors) == 1


def test_rotating_hmac_key_without_migration_invalidates_chain(monkeypatch) -> None:
    _enable_chain(monkeypatch, "first-audit-key-" + ("a" * 40))
    _engine, Factory = _session_factory()
    with Factory() as db:
        ensure_audit_chain_anchor(db)
        db.add(AuditLog(action="security.keyed", entity="security"))
        db.commit()
        assert verify_audit_chain(db)["valid"] is True

        monkeypatch.setenv("AUDIT_CHAIN_HMAC_KEY", "second-audit-key-" + ("b" * 40))
        get_soc_settings.cache_clear()
        report = verify_audit_chain(db)
        assert report["valid"] is False
        assert report["reason"] == "entry_hmac_mismatch"

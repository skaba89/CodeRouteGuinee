import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit_chain import ensure_audit_chain_anchor
from app.db.base import Base
from app.models_audit import AuditLog
from app.soc_config import get_soc_settings


@pytest.fixture(autouse=True)
def _clear_soc_cache_after_test():
    yield
    get_soc_settings.cache_clear()


def _factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[AuditLog.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def _enable(monkeypatch) -> None:
    monkeypatch.setenv("SOC_ENABLED", "true")
    monkeypatch.setenv("SOC_PSEUDONYM_KEY", "p" * 48)
    monkeypatch.setenv("AUDIT_CHAIN_ENABLED", "true")
    monkeypatch.setenv("AUDIT_CHAIN_HMAC_KEY", "a" * 48)
    get_soc_settings.cache_clear()


def test_chained_audit_row_cannot_be_updated_through_orm(monkeypatch) -> None:
    _enable(monkeypatch)
    Factory = _factory()
    with Factory() as db:
        ensure_audit_chain_anchor(db)
        row = AuditLog(action="security.created", entity="security")
        db.add(row)
        db.commit()
        row.action = "security.modified"
        with pytest.raises(RuntimeError, match="append-only"):
            db.commit()
        db.rollback()


def test_chained_audit_row_cannot_be_deleted_through_orm(monkeypatch) -> None:
    _enable(monkeypatch)
    Factory = _factory()
    with Factory() as db:
        ensure_audit_chain_anchor(db)
        row = AuditLog(action="security.created", entity="security")
        db.add(row)
        db.commit()
        db.delete(row)
        with pytest.raises(RuntimeError, match="append-only"):
            db.commit()
        db.rollback()

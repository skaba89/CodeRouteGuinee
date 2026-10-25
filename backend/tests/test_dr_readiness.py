"""Test — vérification de l'état de reprise (DR readiness check)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import delete, update

from app.audit_chain import append_audit, ensure_audit_chain_anchor
from app.db.session import SessionLocal, init_db
from app.models_audit import AuditLog
from app.soc_config import get_soc_settings

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import dr_readiness_check as dr  # noqa: E402


@pytest.fixture
def audit_chain_enabled(monkeypatch):
    monkeypatch.setenv("AUDIT_CHAIN_ENABLED", "true")
    monkeypatch.setenv("AUDIT_CHAIN_HMAC_KEY", "k" * 48)
    get_soc_settings.cache_clear()
    yield
    monkeypatch.delenv("AUDIT_CHAIN_ENABLED")
    monkeypatch.delenv("AUDIT_CHAIN_HMAC_KEY")
    get_soc_settings.cache_clear()


def _fresh_chain(entries: int = 2) -> None:
    init_db()
    with SessionLocal() as db:
        db.execute(delete(AuditLog))
        db.commit()
        ensure_audit_chain_anchor(db)
        for i in range(entries):
            append_audit(db, actor_id="u", action="test", entity="x", entity_id=str(i), details={"n": i})
        db.commit()


def test_dr_check_functions_importable(audit_chain_enabled) -> None:
    """Les fonctions de contrôle DR s'importent et s'exécutent."""
    _fresh_chain()
    ok_chain, msg = dr._check_audit_chain()
    ok_db, _ = dr._check_database()
    assert ok_chain is True, msg
    assert ok_db is True


def test_dr_check_detects_broken_chain(audit_chain_enabled) -> None:
    """Le contrôle détecte une chaîne d'audit altérée directement en base."""
    _fresh_chain()
    with SessionLocal() as db:
        db.execute(update(AuditLog).where(AuditLog.seq == 2).values(details={"tampered": True}))
        db.commit()

    ok_chain, msg = dr._check_audit_chain()
    assert ok_chain is False
    assert "rompue" in msg.lower()


def test_dr_check_reports_disabled_chain_without_crashing() -> None:
    """Régression : une chaîne désactivée faisait planter le contrôle (KeyError)."""
    get_soc_settings.cache_clear()
    init_db()
    ok_chain, msg = dr._check_audit_chain()
    assert ok_chain is False
    assert "désactivée" in msg

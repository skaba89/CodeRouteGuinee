"""
Test — Journal d'audit inviolable (chaîne HMAC P11).

Prouve que le journal détecte toute altération ou suppression d'une entrée
passée, qu'il est append-only au niveau ORM, et que la preuve d'intégrité
est exposée aux seuls administrateurs. Preuve d'intégrité pour un examen d'État.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app.audit_chain import GENESIS_HASH, append_audit, ensure_audit_chain_anchor, verify_audit_chain
from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_audit import AuditLog
from app.soc_config import get_soc_settings
from tests.conftest import get_admin_headers, get_candidate_headers


@pytest.fixture
def audit_chain_enabled(monkeypatch):
    monkeypatch.setenv("AUDIT_CHAIN_ENABLED", "true")
    monkeypatch.setenv("AUDIT_CHAIN_HMAC_KEY", "k" * 48)
    get_soc_settings.cache_clear()
    yield
    monkeypatch.delenv("AUDIT_CHAIN_ENABLED")
    monkeypatch.delenv("AUDIT_CHAIN_HMAC_KEY")
    get_soc_settings.cache_clear()


def _fresh_chain(n: int = 3) -> None:
    """Repart d'un journal vide, ancré, puis ajoute n entrées chaînées."""
    init_db()
    with SessionLocal() as db:
        # Suppression en masse (hors unité de travail ORM) : réservée au test.
        db.execute(delete(AuditLog))
        db.commit()
        ensure_audit_chain_anchor(db)
        for i in range(n):
            append_audit(db, actor_id=f"u{i}", action="exam.submitted",
                         entity="exam", entity_id=f"ex-{i}", details={"score": 30 + i})
        db.commit()


def test_chaine_intacte_est_valide(audit_chain_enabled) -> None:
    _fresh_chain(3)
    with SessionLocal() as db:
        rep = verify_audit_chain(db)
    assert rep["valid"] is True
    assert rep["total_entries"] == 4  # ancre + 3 entrées
    assert rep["broken_at_seq"] is None


def test_ancre_chainee_au_genesis(audit_chain_enabled) -> None:
    _fresh_chain(1)
    with SessionLocal() as db:
        first = db.scalar(select(AuditLog).where(AuditLog.seq == 1))
        second = db.scalar(select(AuditLog).where(AuditLog.seq == 2))
    assert first.action == "audit.chain_anchor"
    assert first.prev_hash == GENESIS_HASH
    assert second.prev_hash == first.entry_hash
    assert second.entry_hash and len(second.entry_hash) == 64


def test_alteration_detectee(audit_chain_enabled) -> None:
    _fresh_chain(3)
    with SessionLocal() as db:
        # Modification frauduleuse directe en base (hors ORM) du score de l'entrée n°3.
        db.execute(update(AuditLog).where(AuditLog.seq == 3).values(details={"score": 40}))
        db.commit()
        rep = verify_audit_chain(db)
    assert rep["valid"] is False
    assert rep["broken_at_seq"] == 3
    assert rep["reason"] == "entry_hmac_mismatch"


def test_suppression_detectee(audit_chain_enabled) -> None:
    _fresh_chain(3)
    with SessionLocal() as db:
        db.execute(delete(AuditLog).where(AuditLog.seq == 3))
        db.commit()
        rep = verify_audit_chain(db)
    assert rep["valid"] is False
    assert rep["reason"] == "sequence_gap"


def test_journal_append_only_via_orm(audit_chain_enabled) -> None:
    _fresh_chain(2)
    with SessionLocal() as db:
        entry = db.scalar(select(AuditLog).where(AuditLog.seq == 2))
        entry.details = {"score": 40}
        with pytest.raises(RuntimeError, match="append-only"):
            db.commit()
        db.rollback()


def test_endpoint_verification_admin(audit_chain_enabled) -> None:
    _fresh_chain(2)
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/ops/audit-chain/verify",
                       headers=get_admin_headers(client))
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["valid"] is True
    assert body["total_entries"] >= 3


def test_endpoint_signale_chaine_desactivee() -> None:
    get_soc_settings.cache_clear()
    init_db()
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/ops/audit-chain/verify",
                       headers=get_admin_headers(client))
    assert r.status_code == 200
    assert r.json() == {"enabled": False, "valid": False, "reason": "disabled"}


def test_endpoint_verification_refuse_candidat() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/ops/audit-chain/verify",
                       headers=get_candidate_headers(client))
        assert r.status_code == 403

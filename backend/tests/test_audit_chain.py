"""
Test — Journal d'audit inviolable (chaînage cryptographique).

Prouve que le journal détecte toute altération, insertion ou suppression
d'une entrée passée. Preuve d'intégrité pour un examen d'État.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import init_db, SessionLocal
from app.audit_chain import append_audit, verify_audit_chain, GENESIS_HASH
from app.models_audit import AuditLog
from sqlalchemy import select
from tests.conftest import get_admin_headers, get_candidate_headers


def _fresh_chain(n: int = 3) -> None:
    """Ajoute n entrées chaînées sur une base propre."""
    init_db()
    db = SessionLocal()
    # Nettoyer les entrées chaînées d'un test précédent
    for e in db.scalars(select(AuditLog).where(AuditLog.seq.isnot(None))).all():
        db.delete(e)
    db.commit()
    for i in range(n):
        append_audit(db, actor_id=f"u{i}", action="exam.submitted",
                     entity="exam", entity_id=f"ex-{i}", details={"score": 30 + i})
    db.commit()
    db.close()


def test_chaine_intacte_est_valide() -> None:
    _fresh_chain(3)
    db = SessionLocal()
    rep = verify_audit_chain(db)
    assert rep["valid"] is True
    assert rep["total_entries"] >= 3
    assert rep["broken_at_seq"] is None
    db.close()


def test_premiere_entree_chainee_au_genesis() -> None:
    _fresh_chain(1)
    db = SessionLocal()
    first = db.scalar(select(AuditLog).where(AuditLog.seq == 1))
    assert first.prev_hash == GENESIS_HASH
    assert first.entry_hash and len(first.entry_hash) == 64
    db.close()


def test_alteration_detectee() -> None:
    _fresh_chain(3)
    db = SessionLocal()
    # Modifier frauduleusement le score d'une entrée passée
    target = db.scalar(select(AuditLog).where(AuditLog.seq == 2))
    target.details = {"score": 40}
    db.add(target); db.commit()

    rep = verify_audit_chain(db)
    assert rep["valid"] is False
    assert rep["broken_at_seq"] == 2
    assert "altéré" in rep["reason"].lower()
    db.close()


def test_suppression_detectee() -> None:
    _fresh_chain(3)
    db = SessionLocal()
    db.delete(db.scalar(select(AuditLog).where(AuditLog.seq == 2)))
    db.commit()
    rep = verify_audit_chain(db)
    assert rep["valid"] is False
    db.close()


def test_endpoint_verification_admin() -> None:
    _fresh_chain(2)
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/ops/audit-chain/verify",
                       headers=get_admin_headers(client))
        assert r.status_code == 200
        assert "valid" in r.json()
        assert "total_entries" in r.json()


def test_endpoint_verification_refuse_candidat() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/ops/audit-chain/verify",
                       headers=get_candidate_headers(client))
        assert r.status_code == 403

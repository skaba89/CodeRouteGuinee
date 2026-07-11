"""Test — vérification de l'état de reprise (DR readiness check)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.db.session import init_db, SessionLocal
from app.audit_chain import append_audit, verify_audit_chain


def test_dr_check_functions_importable() -> None:
    """Les fonctions de contrôle DR s'importent et s'exécutent."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import dr_readiness_check as dr

    init_db()
    db = SessionLocal()
    append_audit(db, actor_id="u", action="test", entity="x", entity_id="1", details={})
    db.commit(); db.close()

    ok_chain, _ = dr._check_audit_chain()
    ok_db, _ = dr._check_database()
    assert ok_chain is True
    assert ok_db is True


def test_dr_check_detects_broken_chain() -> None:
    """Le contrôle détecte une chaîne d'audit corrompue."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import dr_readiness_check as dr
    from app.models_audit import AuditLog
    from sqlalchemy import select

    init_db()
    db = SessionLocal()
    # Nettoyer + créer une chaîne
    for e in db.scalars(select(AuditLog).where(AuditLog.seq.isnot(None))).all():
        db.delete(e)
    db.commit()
    for i in range(2):
        append_audit(db, actor_id="u", action="test", entity="x", entity_id=str(i), details={"n": i})
    db.commit()
    # Corrompre
    target = db.scalar(select(AuditLog).where(AuditLog.seq == 1))
    target.details = {"tampered": True}
    db.add(target); db.commit(); db.close()

    ok_chain, msg = dr._check_audit_chain()
    assert ok_chain is False
    assert "rompue" in msg.lower() or "altéré" in msg.lower()

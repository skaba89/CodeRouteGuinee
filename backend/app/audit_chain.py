"""
Journal d'audit inviolable (tamper-evident) — CodeRoute Guinée.

Chaque entrée d'audit est chaînée cryptographiquement à la précédente :
son empreinte SHA-256 inclut l'empreinte de l'entrée d'avant. Toute
altération ou suppression d'une entrée passée casse la chaîne et devient
détectable lors de la vérification.

Pour un examen d'État, si un résultat est contesté en justice, cette
traçabilité infalsifiable est la preuve de l'intégrité du système.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models_audit import AuditLog

# Empreinte de départ de la chaîne (racine)
GENESIS_HASH = "0" * 64


def _compute_hash(seq: int, actor_id: str | None, action: str, entity: str,
                  entity_id: str | None, details: dict | None,
                  created_at: str, prev_hash: str) -> str:
    """SHA-256 déterministe du contenu d'une entrée + empreinte précédente."""
    payload = json.dumps({
        "seq": seq,
        "actor_id": actor_id,
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "details": details,
        "created_at": created_at,
        "prev_hash": prev_hash,
    }, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_audit(db: Session, *, actor_id: str | None, action: str,
                 entity: str, entity_id: str | None = None,
                 details: dict | None = None) -> AuditLog:
    """
    Ajoute une entrée d'audit chaînée. À utiliser à la place d'une création
    directe d'AuditLog pour les événements sensibles (résultats, paiements,
    validations, décisions). Ne fait PAS de commit (laisse l'appelant maître
    de la transaction).
    """
    # Dernière entrée de la chaîne (seq max)
    last = db.scalar(
        select(AuditLog).where(AuditLog.seq.isnot(None)).order_by(AuditLog.seq.desc()).limit(1)
    )
    seq = (last.seq + 1) if last and last.seq is not None else 1
    prev_hash = last.entry_hash if last and last.entry_hash else GENESIS_HASH

    created_at = datetime.now(UTC).replace(tzinfo=None)
    created_iso = created_at.isoformat()
    entry_hash = _compute_hash(seq, actor_id, action, entity, entity_id,
                               details, created_iso, prev_hash)

    entry = AuditLog(
        actor_id=actor_id, action=action, entity=entity, entity_id=entity_id,
        details=details, created_at=created_at,
        seq=seq, prev_hash=prev_hash, entry_hash=entry_hash,
    )
    db.add(entry)
    # Flush pour que l'entrée soit visible aux appels suivants dans la même
    # transaction (sinon plusieurs append_audit avant commit calculeraient
    # le même seq).
    db.flush()
    return entry


def verify_audit_chain(db: Session) -> dict:
    """
    Vérifie l'intégrité de toute la chaîne d'audit. Retourne un rapport :
      valid          : True si la chaîne est intacte
      total_entries  : nombre d'entrées chaînées vérifiées
      broken_at_seq  : numéro de séquence de la première rupture (ou None)
      reason         : description de la rupture (ou None)

    Une chaîne intacte prouve qu'aucune entrée n'a été altérée, insérée ou
    supprimée depuis sa création.
    """
    entries = list(db.scalars(
        select(AuditLog).where(AuditLog.seq.isnot(None)).order_by(AuditLog.seq.asc())
    ).all())

    if not entries:
        return {"valid": True, "total_entries": 0, "broken_at_seq": None, "reason": None}

    expected_prev = GENESIS_HASH
    expected_seq = 1
    for e in entries:
        # 1. Séquence continue et croissante
        if e.seq != expected_seq:
            return {"valid": False, "total_entries": len(entries),
                    "broken_at_seq": e.seq,
                    "reason": f"Séquence rompue : attendu {expected_seq}, trouvé {e.seq} "
                              "(entrée supprimée ou insérée ?)"}
        # 2. Chaînage : prev_hash pointe bien sur l'entrée précédente
        if e.prev_hash != expected_prev:
            return {"valid": False, "total_entries": len(entries),
                    "broken_at_seq": e.seq,
                    "reason": "Rupture de chaîne : prev_hash ne correspond pas."}
        # 3. Recalcul de l'empreinte : le contenu n'a pas été altéré
        recomputed = _compute_hash(
            e.seq, e.actor_id, e.action, e.entity, e.entity_id, e.details,
            e.created_at.isoformat(), e.prev_hash,
        )
        if recomputed != e.entry_hash:
            return {"valid": False, "total_entries": len(entries),
                    "broken_at_seq": e.seq,
                    "reason": "Contenu altéré : l'empreinte recalculée diffère."}
        expected_prev = e.entry_hash
        expected_seq += 1

    return {"valid": True, "total_entries": len(entries),
            "broken_at_seq": None, "reason": None}

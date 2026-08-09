"""Chaîne HMAC tamper-evident du journal d'audit CodeRoute.

Compatibilité P11 : tout historique préexistant (lignes non chaînées ou ancienne
chaîne SHA-256) est figé dans une ancre P11. La chaîne HMAC commence à cette
ancre sans réécrire l'historique, ce qui évite de casser une base déjà en usage.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from app.models_audit import AuditLog, new_id
from app.soc_config import get_soc_settings

GENESIS_HASH = "0" * 64
_ANCHOR_KIND = "coderoute_audit_legacy_anchor_v2"
_ADVISORY_LOCK_ID = 1129268293


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _canonical_payload(entry: AuditLog, *, seq: int, prev_hash: str) -> bytes:
    payload: dict[str, Any] = {
        "seq": seq,
        "prev_hash": prev_hash,
        "id": entry.id,
        "actor_id": entry.actor_id,
        "action": entry.action,
        "entity": entry.entity,
        "entity_id": entry.entity_id,
        "details": entry.details,
        "created_at": _dt(entry.created_at),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def _compute_hmac(entry: AuditLog, *, seq: int, prev_hash: str, key: str) -> str:
    return hmac.new(
        key.encode("utf-8"),
        _canonical_payload(entry, seq=seq, prev_hash=prev_hash),
        hashlib.sha256,
    ).hexdigest()


def _legacy_digest(entries: list[AuditLog]) -> str:
    digest = hashlib.sha256()
    ordered = sorted(entries, key=lambda item: (_dt(item.created_at) or "", item.id or ""))
    for item in ordered:
        payload = {
            "id": item.id,
            "actor_id": item.actor_id,
            "action": item.action,
            "entity": item.entity,
            "entity_id": item.entity_id,
            "details": item.details,
            "created_at": _dt(item.created_at),
            "seq": item.seq,
            "prev_hash": item.prev_hash,
            "entry_hash": item.entry_hash,
        }
        digest.update(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _lock_chain(db: Session) -> None:
    connection = db.connection()
    if connection.dialect.name == "postgresql":
        connection.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": _ADVISORY_LOCK_ID})


def _chain_head(db: Session) -> tuple[int, str]:
    row = db.connection().execute(
        select(AuditLog.seq, AuditLog.entry_hash)
        .where(AuditLog.seq.is_not(None), AuditLog.entry_hash.is_not(None))
        .order_by(AuditLog.seq.desc())
        .limit(1)
    ).first()
    if not row:
        return 1, GENESIS_HASH
    return int(row.seq) + 1, str(row.entry_hash)


def _p11_anchor(db: Session) -> AuditLog | None:
    rows = list(db.scalars(select(AuditLog).where(AuditLog.action == "audit.chain_anchor")).all())
    for item in rows:
        if isinstance(item.details, dict) and item.details.get("kind") == _ANCHOR_KIND:
            return item
    return None


@event.listens_for(Session, "before_flush")
def _chain_new_audit_rows(db: Session, _flush_context, _instances) -> None:
    settings = get_soc_settings()
    if not settings.audit_chain_enabled:
        return
    if not settings.audit_chain_hmac_key:
        raise RuntimeError("AUDIT_CHAIN_HMAC_KEY absent alors que AUDIT_CHAIN_ENABLED=true")

    pending = [item for item in db.new if isinstance(item, AuditLog) and not item.entry_hash]
    if not pending:
        return

    _lock_chain(db)
    next_seq, prev_hash = _chain_head(db)
    for item in pending:
        if item.id is None:
            item.id = new_id()
        if item.created_at is None:
            item.created_at = datetime.now(UTC).replace(tzinfo=None)
        item.seq = next_seq
        item.prev_hash = prev_hash
        item.entry_hash = _compute_hmac(
            item,
            seq=next_seq,
            prev_hash=prev_hash,
            key=settings.audit_chain_hmac_key,
        )
        prev_hash = item.entry_hash
        next_seq += 1


def append_audit(
    db: Session,
    *,
    actor_id: str | None,
    action: str,
    entity: str,
    entity_id: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(actor_id=actor_id, action=action, entity=entity, entity_id=entity_id, details=details)
    db.add(entry)
    db.flush()
    return entry


def ensure_audit_chain_anchor(db: Session) -> dict:
    """Crée l'ancre P11 une seule fois, même avec plusieurs instances au boot."""
    settings = get_soc_settings()
    if not settings.audit_chain_enabled:
        return {"enabled": False, "created": False}

    _lock_chain(db)
    existing_anchor = _p11_anchor(db)
    if existing_anchor:
        return {"enabled": True, "created": False, "anchor_id": existing_anchor.id}

    legacy = list(db.scalars(select(AuditLog)).all())
    legacy_max_seq = max((int(item.seq or 0) for item in legacy), default=0)
    legacy_head = next(
        (
            item.entry_hash
            for item in sorted(legacy, key=lambda row: int(row.seq or 0), reverse=True)
            if item.seq is not None and item.entry_hash
        ),
        GENESIS_HASH,
    )
    anchor = AuditLog(
        actor_id=None,
        action="audit.chain_anchor",
        entity="audit",
        entity_id=None,
        details={
            "kind": _ANCHOR_KIND,
            "legacy_count": len(legacy),
            "legacy_sha256": _legacy_digest(legacy),
            "legacy_max_seq": legacy_max_seq,
            "legacy_head_hash": legacy_head,
            "activated_at": datetime.now(UTC).isoformat(),
        },
    )
    db.add(anchor)
    db.commit()
    return {
        "enabled": True,
        "created": True,
        "legacy_count": len(legacy),
        "anchor_id": anchor.id,
        "anchor_seq": anchor.seq,
    }


def verify_audit_chain(db: Session) -> dict:
    settings = get_soc_settings()
    if not settings.audit_chain_enabled:
        return {"enabled": False, "valid": False, "reason": "disabled"}
    key = settings.audit_chain_hmac_key
    if not key:
        return {"enabled": True, "valid": False, "reason": "missing_key"}

    anchor = _p11_anchor(db)
    if not anchor or anchor.seq is None or not isinstance(anchor.details, dict):
        return {"enabled": True, "valid": False, "reason": "missing_p11_anchor"}

    anchor_seq = int(anchor.seq)
    legacy = list(
        db.scalars(
            select(AuditLog).where((AuditLog.seq.is_(None)) | (AuditLog.seq < anchor_seq))
        ).all()
    )
    expected_count = int(anchor.details.get("legacy_count", -1))
    expected_digest = str(anchor.details.get("legacy_sha256", ""))
    if expected_count != len(legacy) or not expected_digest or not hmac.compare_digest(expected_digest, _legacy_digest(legacy)):
        return {
            "enabled": True,
            "valid": False,
            "reason": "legacy_anchor_mismatch",
            "legacy_entries": len(legacy),
            "broken_at_seq": None,
        }

    entries = list(
        db.scalars(
            select(AuditLog).where(AuditLog.seq >= anchor_seq).order_by(AuditLog.seq.asc())
        ).all()
    )
    expected_seq = anchor_seq
    expected_prev = anchor.prev_hash or GENESIS_HASH
    for item in entries:
        seq = int(item.seq or 0)
        if seq != expected_seq:
            return {"enabled": True, "valid": False, "total_entries": len(entries), "broken_at_seq": seq, "reason": "sequence_gap"}
        if item.prev_hash != expected_prev:
            return {"enabled": True, "valid": False, "total_entries": len(entries), "broken_at_seq": seq, "reason": "prev_hash_mismatch"}
        recomputed = _compute_hmac(item, seq=seq, prev_hash=item.prev_hash or GENESIS_HASH, key=key)
        if not item.entry_hash or not hmac.compare_digest(item.entry_hash, recomputed):
            return {"enabled": True, "valid": False, "total_entries": len(entries), "broken_at_seq": seq, "reason": "entry_hmac_mismatch"}
        expected_prev = item.entry_hash
        expected_seq += 1

    return {
        "enabled": True,
        "valid": True,
        "total_entries": len(entries),
        "legacy_entries": len(legacy),
        "anchor_seq": anchor_seq,
        "head_seq": int(entries[-1].seq or 0),
        "head_hash": entries[-1].entry_hash,
        "broken_at_seq": None,
        "reason": None,
    }

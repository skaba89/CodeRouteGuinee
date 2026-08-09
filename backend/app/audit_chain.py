"""Chaîne HMAC tamper-evident du journal d'audit CodeRoute.

P11 renforce l'ancien SHA-256 simple :
- HMAC-SHA256 avec clé institutionnelle séparée ;
- advisory transaction lock PostgreSQL pour plusieurs instances API ;
- chaînage automatique de toute nouvelle ligne AuditLog via SQLAlchemy ;
- ancre cryptographique des lignes historiques non chaînées ;
- vérification de la chaîne et de l'ancre legacy.

Le journal reste une preuve applicative. La clé HMAC doit être conservée dans le
coffre de secrets et sa rotation doit suivre une procédure institutionnelle.
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
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


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
        }
        digest.update(
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def _lock_chain(db: Session) -> None:
    connection = db.connection()
    if connection.dialect.name == "postgresql":
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _ADVISORY_LOCK_ID},
        )


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


@event.listens_for(Session, "before_flush")
def _chain_new_audit_rows(db: Session, _flush_context, _instances) -> None:
    """Chaîne automatiquement tout AuditLog ORM non encore signé."""
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
    """Compatibilité : crée un AuditLog ; le hook before_flush signe la ligne."""
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
    db.flush()
    return entry


def ensure_audit_chain_anchor(db: Session) -> dict:
    """Fige une empreinte des anciennes lignes non chaînées avant trafic P11."""
    settings = get_soc_settings()
    if not settings.audit_chain_enabled:
        return {"enabled": False, "created": False}

    existing = db.scalar(select(AuditLog.id).where(AuditLog.seq.is_not(None)).limit(1))
    if existing:
        return {"enabled": True, "created": False}

    legacy = list(db.scalars(select(AuditLog).where(AuditLog.seq.is_(None))).all())
    anchor = AuditLog(
        actor_id=None,
        action="audit.chain_anchor",
        entity="audit",
        entity_id=None,
        details={
            "kind": "coderoute_audit_legacy_anchor_v1",
            "legacy_count": len(legacy),
            "legacy_sha256": _legacy_digest(legacy),
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
    }


def verify_audit_chain(db: Session) -> dict:
    settings = get_soc_settings()
    if not settings.audit_chain_enabled:
        return {"enabled": False, "valid": False, "reason": "disabled"}
    key = settings.audit_chain_hmac_key
    if not key:
        return {"enabled": True, "valid": False, "reason": "missing_key"}

    entries = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.seq.is_not(None))
            .order_by(AuditLog.seq.asc())
        ).all()
    )
    if not entries:
        return {
            "enabled": True,
            "valid": False,
            "total_entries": 0,
            "broken_at_seq": None,
            "reason": "missing_anchor",
        }

    expected_seq = 1
    expected_prev = GENESIS_HASH
    for item in entries:
        seq = int(item.seq or 0)
        if seq != expected_seq:
            return {
                "enabled": True,
                "valid": False,
                "total_entries": len(entries),
                "broken_at_seq": seq,
                "reason": "sequence_gap",
            }
        if item.prev_hash != expected_prev:
            return {
                "enabled": True,
                "valid": False,
                "total_entries": len(entries),
                "broken_at_seq": seq,
                "reason": "prev_hash_mismatch",
            }
        recomputed = _compute_hmac(
            item,
            seq=seq,
            prev_hash=item.prev_hash or GENESIS_HASH,
            key=key,
        )
        if not item.entry_hash or not hmac.compare_digest(item.entry_hash, recomputed):
            return {
                "enabled": True,
                "valid": False,
                "total_entries": len(entries),
                "broken_at_seq": seq,
                "reason": "entry_hmac_mismatch",
            }
        expected_prev = item.entry_hash
        expected_seq += 1

    anchor = next((item for item in entries if item.action == "audit.chain_anchor"), None)
    legacy = list(db.scalars(select(AuditLog).where(AuditLog.seq.is_(None))).all())
    if not anchor or not isinstance(anchor.details, dict):
        return {
            "enabled": True,
            "valid": False,
            "total_entries": len(entries),
            "broken_at_seq": None,
            "reason": "legacy_anchor_missing",
        }
    expected_count = int(anchor.details.get("legacy_count", -1))
    expected_digest = str(anchor.details.get("legacy_sha256", ""))
    actual_digest = _legacy_digest(legacy)
    if expected_count != len(legacy) or not expected_digest or not hmac.compare_digest(expected_digest, actual_digest):
        return {
            "enabled": True,
            "valid": False,
            "total_entries": len(entries),
            "legacy_entries": len(legacy),
            "broken_at_seq": None,
            "reason": "legacy_anchor_mismatch",
        }

    return {
        "enabled": True,
        "valid": True,
        "total_entries": len(entries),
        "legacy_entries": len(legacy),
        "head_seq": int(entries[-1].seq or 0),
        "head_hash": entries[-1].entry_hash,
        "broken_at_seq": None,
        "reason": None,
    }

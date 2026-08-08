from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

EDGE_LEASE_AUTHORITY = "CodeRoute Edge Exam Lease"
EDGE_LEASE_SCOPE_KIND = "center_edge_exam_lease_v1"
EDGE_LEASE_SIGNING_SECRET_ENV = "EDGE_LEASE_SIGNING_SECRET"
EDGE_OFFLINE_FINALIZE_GRACE_MS = 2_000
JOURNAL_GENESIS_HASH = "0" * 64


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_b64url(value: str) -> bytes:
    raw = (value or "").strip()
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _lease_signing_seed() -> bytes:
    secret = os.environ.get(EDGE_LEASE_SIGNING_SECRET_ENV, "").strip()
    if len(secret) < 32:
        raise ValueError(
            f"{EDGE_LEASE_SIGNING_SECRET_ENV} doit contenir au moins 32 caractères pour émettre des leases Edge"
        )
    return hashlib.sha256(b"coderoute-edge-lease-v1\x00" + secret.encode("utf-8")).digest()


def lease_signing_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(_lease_signing_seed())


def lease_signing_public_key_b64() -> str:
    raw = lease_signing_private_key().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64url(raw)


def lease_signing_key_id() -> str:
    raw = _decode_b64url(lease_signing_public_key_b64())
    return f"edge-lease-v1:{sha256_hex(raw)[:16]}"


def sign_lease_payload(payload: dict[str, Any]) -> tuple[str, str, str]:
    encoded = canonical_json(payload)
    digest = sha256_hex(encoded)
    signature = lease_signing_private_key().sign(encoded)
    return digest, _b64url(signature), lease_signing_key_id()


def verify_lease_signature(
    payload: dict[str, Any],
    signature_b64: str,
    public_key_b64: str | None = None,
) -> bool:
    try:
        raw_public = _decode_b64url(public_key_b64 or lease_signing_public_key_b64())
        raw_signature = _decode_b64url(signature_b64)
        Ed25519PublicKey.from_public_bytes(raw_public).verify(raw_signature, canonical_json(payload))
        return True
    except Exception:
        return False


def machine_action_payload(
    *,
    action: str,
    node_id: str,
    center_id: str,
    sequence: int,
    sent_at: str,
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "action": action,
        "center_id": center_id,
        "node_id": node_id,
        "sent_at": sent_at,
        "sequence": int(sequence),
    }
    if fields:
        payload.update(fields)
    return payload


def compute_journal_event_hash(
    *,
    lease_id: str,
    sequence: int,
    elapsed_ms: int,
    question_id: str,
    answer: str,
    prev_hash: str,
) -> str:
    payload = {
        "answer": answer,
        "elapsed_ms": int(elapsed_ms),
        "lease_id": lease_id,
        "prev_hash": prev_hash,
        "question_id": question_id,
        "sequence": int(sequence),
    }
    return sha256_hex(canonical_json(payload))


def verify_answer_journal(
    *,
    lease_id: str,
    events: list[dict[str, Any]],
    allowed_options: dict[str, set[str]],
    expected_head_hash: str,
    finalized_elapsed_ms: int,
    duration_ms: int,
) -> dict[str, Any]:
    if finalized_elapsed_ms < 0:
        raise ValueError("Temps de finalisation négatif")
    if finalized_elapsed_ms > duration_ms + EDGE_OFFLINE_FINALIZE_GRACE_MS:
        raise ValueError("Finalisation Edge postérieure à la deadline du lease")

    expected_prev = JOURNAL_GENESIS_HASH
    expected_sequence = 1
    previous_elapsed = 0
    answers: dict[str, str] = {}

    for event in events:
        sequence = int(event.get("sequence") or 0)
        elapsed_ms = int(event.get("elapsed_ms") or 0)
        question_id = str(event.get("question_id") or "")
        answer = str(event.get("answer") or "")
        prev_hash = str(event.get("prev_hash") or "")
        event_hash = str(event.get("event_hash") or "")

        if sequence != expected_sequence:
            raise ValueError(f"Séquence journal invalide : attendu {expected_sequence}, reçu {sequence}")
        if elapsed_ms < previous_elapsed:
            raise ValueError("Le temps monotone du journal doit être croissant")
        if elapsed_ms > finalized_elapsed_ms:
            raise ValueError("Un événement du journal survient après la finalisation")
        if question_id not in allowed_options:
            raise ValueError("Question absente du lease Edge")
        if answer not in allowed_options[question_id]:
            raise ValueError("Réponse absente des options autorisées par le lease")
        if prev_hash != expected_prev:
            raise ValueError("Chaînage du journal Edge rompu")

        computed = compute_journal_event_hash(
            lease_id=lease_id,
            sequence=sequence,
            elapsed_ms=elapsed_ms,
            question_id=question_id,
            answer=answer,
            prev_hash=prev_hash,
        )
        if computed != event_hash:
            raise ValueError("Empreinte d'événement Edge invalide")

        answers[question_id] = answer
        expected_prev = event_hash
        expected_sequence += 1
        previous_elapsed = elapsed_ms

    actual_head = expected_prev
    if actual_head != expected_head_hash:
        raise ValueError("Empreinte finale du journal Edge incohérente")

    return {
        "answers": answers,
        "event_count": len(events),
        "journal_head_hash": actual_head,
        "last_elapsed_ms": previous_elapsed if events else 0,
    }


def encode_lease_scope(scope: dict[str, Any]) -> str:
    return json.dumps(scope, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def decode_lease_scope(raw_scope: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw_scope or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Scope de lease Edge illisible") from exc
    if not isinstance(data, dict) or data.get("kind") != EDGE_LEASE_SCOPE_KIND:
        raise ValueError("Autorisation non associée à un lease Edge")
    return data


def utc_iso(value: datetime) -> str:
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.isoformat(timespec="milliseconds").replace("+00:00", "Z")

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

EDGE_AUTHORITY = "CodeRoute Edge Gateway"
EDGE_SCOPE_KIND = "center_edge_node"
EDGE_HEARTBEAT_INTERVAL_SECONDS = 60
EDGE_HEARTBEAT_MAX_SKEW_SECONDS = 300
EDGE_ONLINE_GRACE_SECONDS = 180
EDGE_TARGET_SOFTWARE_VERSION = os.environ.get("CODEROUTE_EDGE_TARGET_VERSION", "edge-agent-0.4.0").strip() or "edge-agent-0.4.0"
EDGE_REQUIRED_CAPABILITIES = (
    "answer-journal-v1",
    "exam-lease-v1",
    "fleet-telemetry-v1",
    "maintenance-updater-v1",
    "media-prefetch-v1",
    "operator-status-v1",
    "release-attestation-v1",
    "release-key-rotation-v1",
    "release-staging-v1",
    "supply-chain-evidence-v1",
)


def _decode_urlsafe_b64(value: str) -> bytes:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Valeur base64 vide")
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(raw + padding)
    except Exception as exc:
        raise ValueError("Valeur base64 invalide") from exc


def _encode_urlsafe_b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def normalize_public_key_b64(public_key_b64: str) -> str:
    """Valide et normalise une clé publique Ed25519 brute (32 octets)."""
    raw = _decode_urlsafe_b64(public_key_b64)
    if len(raw) != 32:
        raise ValueError("Une clé publique Ed25519 doit contenir exactement 32 octets")
    try:
        Ed25519PublicKey.from_public_bytes(raw)
    except Exception as exc:
        raise ValueError("Clé publique Ed25519 invalide") from exc
    return _encode_urlsafe_b64(raw)


def public_key_fingerprint(public_key_b64: str) -> str:
    normalized = normalize_public_key_b64(public_key_b64)
    return hashlib.sha256(_decode_urlsafe_b64(normalized)).hexdigest()


def normalize_capabilities(capabilities: list[str] | None) -> list[str]:
    clean = {
        str(value).strip().lower()
        for value in (capabilities or [])
        if str(value).strip()
    }
    return sorted(clean)[:32]


def _safe_non_negative_int(value: Any, *, maximum: int) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        parsed = 0
    return min(max(parsed, 0), maximum)


def normalize_heartbeat_telemetry(telemetry: dict[str, Any] | None) -> dict[str, int] | None:
    """Normalise uniquement la télémétrie d'exploitation autorisée.

    Le heartbeat national ne doit jamais transporter de question, réponse,
    identité candidat, token ou contenu de journal.
    """
    if telemetry is None:
        return None
    return {
        "active_leases": _safe_non_negative_int(telemetry.get("active_leases"), maximum=100_000),
        "finalized_leases": _safe_non_negative_int(telemetry.get("finalized_leases"), maximum=100_000),
        "synced_leases": _safe_non_negative_int(telemetry.get("synced_leases"), maximum=10_000_000),
        "sync_pending": _safe_non_negative_int(telemetry.get("sync_pending"), maximum=100_000),
        "revalidation_required": _safe_non_negative_int(telemetry.get("revalidation_required"), maximum=100_000),
        "corrupt_leases": _safe_non_negative_int(telemetry.get("corrupt_leases"), maximum=100_000),
        "media_files": _safe_non_negative_int(telemetry.get("media_files"), maximum=1_000_000),
        "media_bytes": _safe_non_negative_int(telemetry.get("media_bytes"), maximum=10_000_000_000_000),
    }


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def iso_z(value: datetime) -> str:
    return normalize_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_edge_payload(payload: dict[str, Any]) -> bytes:
    """Sérialisation canonique signée par le gateway local."""
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def heartbeat_signing_payload(
    *,
    node_id: str,
    center_id: str,
    sequence: int,
    sent_at: datetime,
    software_version: str,
    capabilities: list[str] | None,
    telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "capabilities": normalize_capabilities(capabilities),
        "center_id": center_id,
        "node_id": node_id,
        "sent_at": iso_z(sent_at),
        "sequence": int(sequence),
        "software_version": (software_version or "unknown").strip()[:80],
    }
    normalized_telemetry = normalize_heartbeat_telemetry(telemetry)
    if normalized_telemetry is not None:
        payload["telemetry"] = normalized_telemetry
    return payload


def verify_edge_signature(
    public_key_b64: str,
    payload: dict[str, Any],
    signature_b64: str,
) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            _decode_urlsafe_b64(normalize_public_key_b64(public_key_b64))
        )
        signature = _decode_urlsafe_b64(signature_b64)
        if len(signature) != 64:
            return False
        public_key.verify(signature, canonical_edge_payload(payload))
        return True
    except (InvalidSignature, ValueError):
        return False


def encode_edge_scope(scope: dict[str, Any]) -> str:
    return json.dumps(scope, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def decode_edge_scope(raw_scope: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw_scope or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Scope Edge illisible") from exc
    if not isinstance(data, dict) or data.get("kind") != EDGE_SCOPE_KIND:
        raise ValueError("Autorisation non associée à un nœud Edge")
    return data


def build_edge_scope(
    *,
    node_id: str,
    center_id: str,
    center_code: str,
    label: str,
    public_key_b64: str,
    capabilities: list[str] | None,
    created_by_id: str | None,
    created_at: datetime,
) -> dict[str, Any]:
    normalized_key = normalize_public_key_b64(public_key_b64)
    return {
        "kind": EDGE_SCOPE_KIND,
        "node_id": node_id,
        "center_id": center_id,
        "center_code": center_code,
        "label": label.strip()[:120],
        "public_key_b64": normalized_key,
        "public_key_fingerprint": public_key_fingerprint(normalized_key),
        "capabilities": normalize_capabilities(capabilities),
        "created_by_id": created_by_id,
        "created_at": iso_z(created_at),
        "last_sequence": 0,
        "last_seen_at": None,
        "last_software_version": None,
        "last_clock_skew_seconds": None,
        "last_telemetry": None,
        "last_telemetry_at": None,
    }


def parse_optional_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return normalize_utc(parsed)


def node_is_online(scope: dict[str, Any], *, now: datetime | None = None) -> bool:
    last_seen = parse_optional_iso(scope.get("last_seen_at"))
    if last_seen is None:
        return False
    reference = normalize_utc(now or datetime.now(UTC))
    return (reference - last_seen).total_seconds() <= EDGE_ONLINE_GRACE_SECONDS

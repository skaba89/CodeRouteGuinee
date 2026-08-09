from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
from typing import Any
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.edge_offline import EDGE_LEASE_SIGNING_SECRET_ENV, canonical_json, sha256_hex

EDGE_RELEASE_AUTHORITY = "CodeRoute Edge Software Release"
EDGE_RELEASE_ATTESTATION_AUTHORITY = "CodeRoute Edge Release Attestation"
EDGE_RELEASE_SCOPE_KIND = "center_edge_software_release_v1"
EDGE_RELEASE_ATTESTATION_SCOPE_KIND = "center_edge_release_attestation_v1"
EDGE_RELEASE_MANIFEST_KIND = "center_edge_release_manifest_v1"
EDGE_RELEASE_MAX_BYTES = int(os.environ.get("CODEROUTE_EDGE_RELEASE_MAX_BYTES", str(512 * 1024 * 1024)))
EDGE_RELEASE_ALLOWED_STATUSES = {"draft", "canary", "rolling", "released", "paused", "rollback", "revoked"}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_b64url(value: str) -> bytes:
    raw = (value or "").strip()
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _release_signing_seed() -> bytes:
    secret = os.environ.get(EDGE_LEASE_SIGNING_SECRET_ENV, "").strip()
    if len(secret) < 32:
        raise ValueError(
            f"{EDGE_LEASE_SIGNING_SECRET_ENV} doit contenir au moins 32 caractères pour signer les releases Edge"
        )
    # Même racine institutionnelle que les leases, mais domaine cryptographique distinct.
    return hashlib.sha256(b"coderoute-edge-release-v1\x00" + secret.encode("utf-8")).digest()


def release_signing_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(_release_signing_seed())


def release_signing_public_key_b64() -> str:
    raw = release_signing_private_key().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64url(raw)


def release_signing_key_id() -> str:
    raw = _decode_b64url(release_signing_public_key_b64())
    return f"edge-release-v1:{sha256_hex(raw)[:16]}"


def sign_release_manifest(manifest: dict[str, Any]) -> tuple[str, str, str]:
    encoded = canonical_json(manifest)
    digest = sha256_hex(encoded)
    signature = release_signing_private_key().sign(encoded)
    return digest, _b64url(signature), release_signing_key_id()


def verify_release_manifest(
    manifest: dict[str, Any],
    signature_b64: str,
    public_key_b64: str | None = None,
) -> bool:
    try:
        public_key = _decode_b64url(public_key_b64 or release_signing_public_key_b64())
        signature = _decode_b64url(signature_b64)
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, canonical_json(manifest))
        return True
    except Exception:
        return False


def validate_release_artifact_url(value: str) -> str:
    parsed = urlsplit((value or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("L'artefact Edge doit utiliser une URL HTTPS sans identifiants")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise ValueError("L'artefact Edge ne peut pas pointer vers un hôte local")
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None
    if ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved):
        raise ValueError("L'artefact Edge ne peut pas pointer vers une adresse IP privée ou réservée")
    return parsed.geturl()


def normalize_sha256(value: str) -> str:
    digest = (value or "").strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("SHA-256 d'artefact invalide")
    return digest


def build_release_manifest(
    *,
    release_id: str,
    software_version: str,
    artifact_url: str,
    artifact_sha256: str,
    artifact_size_bytes: int,
    created_at: str,
    min_current_version: str | None,
    release_notes: str | None,
) -> dict[str, Any]:
    if artifact_size_bytes <= 0 or artifact_size_bytes > EDGE_RELEASE_MAX_BYTES:
        raise ValueError("Taille d'artefact Edge invalide ou supérieure à la limite nationale")
    version = software_version.strip()
    if not version or len(version) > 80:
        raise ValueError("Version Edge invalide")
    return {
        "kind": EDGE_RELEASE_MANIFEST_KIND,
        "version": 1,
        "release_id": release_id,
        "software_version": version,
        "artifact": {
            "format": "tar.gz",
            "url": validate_release_artifact_url(artifact_url),
            "sha256": normalize_sha256(artifact_sha256),
            "size_bytes": int(artifact_size_bytes),
        },
        "created_at": created_at,
        "min_current_version": (min_current_version or "").strip() or None,
        "release_notes": (release_notes or "").strip()[:4000] or None,
    }


def deterministic_rollout_bucket(release_id: str, node_id: str) -> int:
    raw = hashlib.sha256(f"{release_id}:{node_id}".encode("utf-8")).digest()
    return int.from_bytes(raw[:4], "big") % 100


def release_is_eligible(
    scope: dict[str, Any],
    *,
    node_id: str,
    center_id: str,
) -> bool:
    status = str(scope.get("rollout_status") or "draft")
    if status not in {"canary", "rolling", "released", "rollback"}:
        return False
    allowed_centers = {str(value) for value in scope.get("allowed_center_ids") or [] if value}
    if allowed_centers and center_id not in allowed_centers:
        return False
    if status == "canary":
        return node_id in {str(value) for value in scope.get("canary_node_ids") or [] if value}
    if status == "rolling":
        percent = max(0, min(100, int(scope.get("rollout_percent") or 0)))
        return deterministic_rollout_bucket(str(scope.get("release_id") or ""), node_id) < percent
    return True


def encode_release_scope(scope: dict[str, Any]) -> str:
    return json.dumps(scope, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def decode_release_scope(raw_scope: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw_scope or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Scope de release Edge illisible") from exc
    if not isinstance(data, dict) or data.get("kind") != EDGE_RELEASE_SCOPE_KIND:
        raise ValueError("Autorisation non associée à une release Edge")
    return data


def encode_attestation_scope(scope: dict[str, Any]) -> str:
    return json.dumps(scope, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def decode_attestation_scope(raw_scope: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw_scope or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Attestation de release Edge illisible") from exc
    if not isinstance(data, dict) or data.get("kind") != EDGE_RELEASE_ATTESTATION_SCOPE_KIND:
        raise ValueError("Autorisation non associée à une attestation de release Edge")
    return data

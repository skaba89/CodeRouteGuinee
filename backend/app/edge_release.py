from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
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
EDGE_RELEASE_SIGNING_SECRET_ENV = "EDGE_RELEASE_SIGNING_SECRET"
EDGE_RELEASE_PREVIOUS_SIGNING_SECRETS_ENV = "EDGE_RELEASE_PREVIOUS_SIGNING_SECRETS"
_HEX_COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_b64url(value: str) -> bytes:
    raw = (value or "").strip()
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _release_signing_secret() -> str:
    # P9 sépare la clé de distribution de celle des leases. Le fallback permet
    # une migration progressive depuis P8 sans coupure nationale.
    secret = os.environ.get(EDGE_RELEASE_SIGNING_SECRET_ENV, "").strip()
    if not secret:
        secret = os.environ.get(EDGE_LEASE_SIGNING_SECRET_ENV, "").strip()
    if len(secret) < 32:
        raise ValueError(
            f"{EDGE_RELEASE_SIGNING_SECRET_ENV} (ou fallback {EDGE_LEASE_SIGNING_SECRET_ENV}) "
            "doit contenir au moins 32 caractères pour signer les releases Edge"
        )
    return secret


def _release_signing_seed(secret: str | None = None) -> bytes:
    value = secret or _release_signing_secret()
    if len(value) < 32:
        raise ValueError("Secret de signature release Edge trop court")
    return hashlib.sha256(b"coderoute-edge-release-v1\x00" + value.encode("utf-8")).digest()


def _public_key_b64_from_secret(secret: str) -> str:
    private_key = Ed25519PrivateKey.from_private_bytes(_release_signing_seed(secret))
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64url(raw)


def _key_id_from_public(public_key_b64: str) -> str:
    raw = _decode_b64url(public_key_b64)
    return f"edge-release-v1:{sha256_hex(raw)[:16]}"


def release_signing_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(_release_signing_seed())


def release_signing_public_key_b64() -> str:
    return _public_key_b64_from_secret(_release_signing_secret())


def release_signing_key_id() -> str:
    return _key_id_from_public(release_signing_public_key_b64())


def release_trusted_public_keys() -> list[dict[str, Any]]:
    active_secret = _release_signing_secret()
    candidates: list[tuple[str, bool]] = [(active_secret, True)]
    raw_previous = os.environ.get(EDGE_RELEASE_PREVIOUS_SIGNING_SECRETS_ENV, "")
    for value in raw_previous.split(","):
        secret = value.strip()
        if secret and secret != active_secret and len(secret) >= 32:
            candidates.append((secret, False))

    seen: set[str] = set()
    keys: list[dict[str, Any]] = []
    for secret, active in candidates:
        public = _public_key_b64_from_secret(secret)
        key_id = _key_id_from_public(public)
        if key_id in seen:
            continue
        seen.add(key_id)
        keys.append({"key_id": key_id, "public_key_b64": public, "active": active})
    return keys


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


def validate_public_https_url(value: str, *, label: str) -> str:
    try:
        return validate_release_artifact_url(value)
    except ValueError as exc:
        raise ValueError(f"{label} invalide : {exc}") from exc


def normalize_sha256(value: str) -> str:
    digest = (value or "").strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("SHA-256 d'artefact invalide")
    return digest


def normalize_supply_chain_evidence(value: dict[str, Any] | None, *, artifact_sha256: str) -> dict[str, Any] | None:
    if value is None:
        return None
    source_commit = str(value.get("source_commit_sha") or "").strip().lower()
    if not _HEX_COMMIT_RE.fullmatch(source_commit):
        raise ValueError("Commit source de supply chain invalide")
    sbom_sha = normalize_sha256(str(value.get("sbom_sha256") or ""))
    subject_digest = normalize_sha256(str(value.get("subject_sha256") or ""))
    if subject_digest != normalize_sha256(artifact_sha256):
        raise ValueError("Le digest attesté doit être identique au SHA-256 de l'artefact")
    scan_status = str(value.get("vulnerability_scan_status") or "").strip().lower()
    if scan_status not in {"passed", "failed"}:
        raise ValueError("Statut du scan de vulnérabilités invalide")
    workflow_ref = str(value.get("workflow_ref") or "").strip()
    if not workflow_ref or len(workflow_ref) > 500:
        raise ValueError("Référence de workflow supply chain invalide")
    provenance_url = validate_public_https_url(str(value.get("provenance_url") or ""), label="URL de provenance")
    sbom_attestation_url_raw = str(value.get("sbom_attestation_url") or "").strip()
    sbom_attestation_url = (
        validate_public_https_url(sbom_attestation_url_raw, label="URL d'attestation SBOM")
        if sbom_attestation_url_raw
        else None
    )
    return {
        "builder": str(value.get("builder") or "github-actions").strip()[:120] or "github-actions",
        "source_commit_sha": source_commit,
        "workflow_ref": workflow_ref,
        "provenance_url": provenance_url,
        "sbom_sha256": sbom_sha,
        "sbom_attestation_url": sbom_attestation_url,
        "subject_sha256": subject_digest,
        "vulnerability_scan_status": scan_status,
    }


def supply_chain_ready(manifest: dict[str, Any]) -> bool:
    evidence = manifest.get("supply_chain")
    if not isinstance(evidence, dict):
        return False
    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    try:
        return (
            str(evidence.get("vulnerability_scan_status") or "") == "passed"
            and normalize_sha256(str(evidence.get("subject_sha256") or ""))
            == normalize_sha256(str(artifact.get("sha256") or ""))
            and bool(_HEX_COMMIT_RE.fullmatch(str(evidence.get("source_commit_sha") or "")))
            and bool(str(evidence.get("workflow_ref") or "").strip())
            and bool(str(evidence.get("provenance_url") or "").strip())
            and bool(normalize_sha256(str(evidence.get("sbom_sha256") or "")))
        )
    except ValueError:
        return False


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
    supply_chain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if artifact_size_bytes <= 0 or artifact_size_bytes > EDGE_RELEASE_MAX_BYTES:
        raise ValueError("Taille d'artefact Edge invalide ou supérieure à la limite nationale")
    version = software_version.strip()
    if not version or len(version) > 80:
        raise ValueError("Version Edge invalide")
    artifact_digest = normalize_sha256(artifact_sha256)
    normalized_supply_chain = normalize_supply_chain_evidence(supply_chain, artifact_sha256=artifact_digest)
    return {
        "kind": EDGE_RELEASE_MANIFEST_KIND,
        "version": 2 if normalized_supply_chain is not None else 1,
        "release_id": release_id,
        "software_version": version,
        "artifact": {
            "format": "tar.gz",
            "url": validate_release_artifact_url(artifact_url),
            "sha256": artifact_digest,
            "size_bytes": int(artifact_size_bytes),
        },
        "created_at": created_at,
        "min_current_version": (min_current_version or "").strip() or None,
        "release_notes": (release_notes or "").strip()[:4000] or None,
        "supply_chain": normalized_supply_chain,
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

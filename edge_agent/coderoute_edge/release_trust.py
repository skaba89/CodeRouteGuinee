from __future__ import annotations

import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex, verify_signed_payload

_INSTALL_AUTH_KIND = "center_edge_install_authorization_v1"


def _load_trust_store(path: Path) -> list[dict[str, Any]]:
    try:
        metadata = path.stat()
    except OSError as exc:
        raise RuntimeError(f"Trust store de release Edge introuvable : {path}") from exc
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeError("Trust store de release Edge insécurisé : écriture groupe/autres interdite")
    if os.geteuid() == 0 and metadata.st_uid != 0:
        raise RuntimeError("Trust store de release Edge doit appartenir à root")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Trust store de release Edge illisible") from exc
    keys = payload.get("trusted_keys") if isinstance(payload, dict) else None
    if not isinstance(keys, list) or not keys:
        raise RuntimeError("Trust store de release Edge vide")
    clean: list[dict[str, Any]] = []
    for item in keys:
        if not isinstance(item, dict):
            continue
        key_id = str(item.get("key_id") or "").strip()
        public_key = str(item.get("public_key_b64") or "").strip()
        if key_id and public_key:
            clean.append({"key_id": key_id, "public_key_b64": public_key})
    if not clean:
        raise RuntimeError("Aucune clé publique exploitable dans le trust store Edge")
    return clean


def _trusted_key(trusted_keys: list[dict[str, Any]], key_id: str) -> str:
    public_key = next((item["public_key_b64"] for item in trusted_keys if item["key_id"] == key_id), None)
    if not public_key:
        raise RuntimeError(f"Clé de signature release non approuvée localement : {key_id or 'absente'}")
    return str(public_key)


def _parse_utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"Horodatage {label} invalide") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _verify_install_authorization(
    staged: dict[str, Any],
    trusted_keys: list[dict[str, Any]],
    *,
    expected_node_id: str,
    expected_center_id: str,
    expected_current_version: str,
    release_id: str,
    version: str,
    artifact_sha256: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    authorization = staged.get("install_authorization")
    if not isinstance(authorization, dict):
        raise RuntimeError("Autorisation centrale d'installation absente du staging P9")
    payload = authorization.get("payload")
    if not isinstance(payload, dict) or payload.get("kind") != _INSTALL_AUTH_KIND:
        raise RuntimeError("Autorisation centrale d'installation invalide")
    key_id = str(authorization.get("signing_key_id") or "")
    public_key = _trusted_key(trusted_keys, key_id)
    signature = str(authorization.get("signature_b64") or "")
    if not verify_signed_payload(public_key, payload, signature):
        raise RuntimeError("Signature Ed25519 de l'autorisation d'installation invalide")
    payload_hash = sha256_hex(canonical_json(payload))
    if payload_hash != str(authorization.get("payload_hash") or ""):
        raise RuntimeError("Hash de l'autorisation d'installation incohérent")

    action = str(staged.get("action") or "install")
    source_release_id = str(staged.get("source_release_id") or "") or None
    checks = {
        "release_id": release_id,
        "source_release_id": source_release_id,
        "node_id": expected_node_id,
        "center_id": expected_center_id,
        "action": action,
        "current_version": expected_current_version,
        "software_version": version,
        "artifact_sha256": artifact_sha256,
    }
    for field, expected in checks.items():
        actual = payload.get(field)
        if actual != expected:
            raise RuntimeError(
                f"Autorisation d'installation non applicable : {field}={actual!r}, attendu {expected!r}"
            )

    issued_at = _parse_utc(str(payload.get("issued_at") or ""), "issued_at")
    expires_at = _parse_utc(str(payload.get("expires_at") or ""), "expires_at")
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    reference = reference.astimezone(UTC)
    if expires_at <= issued_at or reference < issued_at or reference >= expires_at:
        raise RuntimeError("Autorisation centrale d'installation expirée ou hors fenêtre de validité")
    if (expires_at - issued_at).total_seconds() > 3600:
        raise RuntimeError("Autorisation centrale d'installation anormalement longue")
    return {
        "authorization_key_id": key_id,
        "authorization_hash": payload_hash,
        "issued_at": payload["issued_at"],
        "expires_at": payload["expires_at"],
    }


def verify_staged_release_for_root(
    staged: dict[str, Any],
    *,
    release_root: Path,
    trust_store_path: Path,
    expected_node_id: str,
    expected_center_id: str,
    expected_current_version: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Vérification indépendante du daemon avant toute action privilégiée."""
    manifest = staged.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("kind") != "center_edge_release_manifest_v1":
        raise RuntimeError("Manifest signé absent du staging P9")
    signature = str(staged.get("manifest_signature_b64") or "")
    key_id = str(staged.get("signing_key_id") or "")
    trusted_keys = _load_trust_store(trust_store_path)
    public_key = _trusted_key(trusted_keys, key_id)
    if not verify_signed_payload(public_key, manifest, signature):
        raise RuntimeError("Signature Ed25519 du manifest de release invalide côté updater root")

    canonical_hash = sha256_hex(canonical_json(manifest))
    if canonical_hash != str(staged.get("manifest_hash") or ""):
        raise RuntimeError("Hash canonique du manifest différent du staging")

    release_id = str(manifest.get("release_id") or "")
    version = str(manifest.get("software_version") or "")
    if release_id != str(staged.get("release_id") or "") or version != str(staged.get("software_version") or ""):
        raise RuntimeError("Identité/version staged différente du manifest signé")

    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    sha = str(artifact.get("sha256") or "").lower()
    size = int(artifact.get("size_bytes") or 0)
    if sha != str(staged.get("artifact_sha256") or "").lower() or size != int(staged.get("artifact_size_bytes") or 0):
        raise RuntimeError("SHA/taille staged différents du manifest signé")

    expected_artifact = (release_root / f"{release_id}.tar.gz").resolve()
    actual_artifact = Path(str(staged.get("artifact_path") or "")).resolve()
    if actual_artifact != expected_artifact or actual_artifact.parent != release_root.resolve():
        raise RuntimeError("Chemin d'artefact staged hors du répertoire de release approuvé")

    if str(staged.get("action") or "install") != "rollback":
        evidence = manifest.get("supply_chain")
        if not isinstance(evidence, dict):
            raise RuntimeError("Preuve de supply chain absente du manifest P9")
        if str(evidence.get("vulnerability_scan_status") or "") != "passed":
            raise RuntimeError("Scan de vulnérabilités non validé pour cette release")
        if str(evidence.get("subject_sha256") or "").lower() != sha:
            raise RuntimeError("Digest supply chain différent de l'artefact signé")
        if not str(evidence.get("source_commit_sha") or "").strip() or not str(evidence.get("provenance_url") or "").strip():
            raise RuntimeError("Provenance supply chain incomplète")
        if not str(evidence.get("sbom_sha256") or "").strip():
            raise RuntimeError("Empreinte SBOM absente")

    install_auth = _verify_install_authorization(
        staged,
        trusted_keys,
        expected_node_id=expected_node_id,
        expected_center_id=expected_center_id,
        expected_current_version=expected_current_version,
        release_id=release_id,
        version=version,
        artifact_sha256=sha,
        now=now,
    )
    return {
        "release_id": release_id,
        "software_version": version,
        "artifact_sha256": sha,
        "artifact_size_bytes": size,
        "signing_key_id": key_id,
        "manifest_hash": canonical_hash,
        **install_auth,
    }

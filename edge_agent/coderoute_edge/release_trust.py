from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from .crypto import canonical_json, sha256_hex, verify_signed_payload


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


def verify_staged_release_for_root(
    staged: dict[str, Any],
    *,
    release_root: Path,
    trust_store_path: Path,
) -> dict[str, Any]:
    """Vérification indépendante du daemon avant toute action privilégiée."""
    manifest = staged.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("kind") != "center_edge_release_manifest_v1":
        raise RuntimeError("Manifest signé absent du staging P9")
    signature = str(staged.get("manifest_signature_b64") or "")
    key_id = str(staged.get("signing_key_id") or "")
    trusted_keys = _load_trust_store(trust_store_path)
    public_key = next((item["public_key_b64"] for item in trusted_keys if item["key_id"] == key_id), None)
    if not public_key:
        raise RuntimeError(f"Clé de signature release non approuvée localement : {key_id or 'absente'}")
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

    # Les nouvelles installations P9 exigent la supply chain complète. Un
    # rollback peut cibler une release P8 antérieure déjà publiée : dans ce cas,
    # la signature institutionnelle locale reste le garde racine.
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

    return {
        "release_id": release_id,
        "software_version": version,
        "artifact_sha256": sha,
        "artifact_size_bytes": size,
        "signing_key_id": key_id,
        "manifest_hash": canonical_hash,
    }

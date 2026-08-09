from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx

from .central import CentralClient
from .config import EdgeAgentConfig

_VERSION_NUMBERS = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:$|[^0-9])")


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    match = _VERSION_NUMBERS.search((value or "").strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _meets_minimum(current: str, minimum: str | None) -> bool:
    if not minimum:
        return True
    current_tuple = _version_tuple(current)
    minimum_tuple = _version_tuple(minimum)
    return current_tuple is not None and minimum_tuple is not None and current_tuple >= minimum_tuple


class EdgeReleaseManager:
    """Gestion non privilégiée des releases.

    Ce composant peut vérifier et télécharger un artefact, mais ne modifie jamais
    le code en cours d'exécution. L'activation est confiée à l'updater local.
    """

    def __init__(self, config: EdgeAgentConfig, central: CentralClient):
        self.config = config
        self.central = central
        self.root = config.release_dir
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def staged_state_path(self) -> Path:
        return self.root / "staged.json"

    @property
    def install_receipt_path(self) -> Path:
        return self.root / "install-receipt.json"

    def check(self) -> dict[str, Any]:
        return self.central.check_release(self.config.software_version)

    @staticmethod
    def _validate_artifact_url(value: str) -> str:
        parsed = urlsplit((value or "").strip())
        if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise RuntimeError("Release Edge refusée : URL artefact HTTPS invalide")
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
            raise RuntimeError("Release Edge refusée : hôte artefact local")
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            ip = None
        if ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved):
            raise RuntimeError("Release Edge refusée : adresse artefact privée ou réservée")
        return parsed.geturl()

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def _download_verified(self, url: str, tmp_path: Path, expected_size: int) -> tuple[str, int]:
        """Télécharge sans cookies du central et revalide chaque redirection."""
        current_url = self._validate_artifact_url(url)
        digest = hashlib.sha256()
        total = 0
        with httpx.Client(timeout=60.0, follow_redirects=False) as downloader:
            for redirect_count in range(4):
                with downloader.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location or redirect_count >= 3:
                            raise RuntimeError("Chaîne de redirection de release Edge invalide")
                        current_url = self._validate_artifact_url(urljoin(current_url, location))
                        continue
                    response.raise_for_status()
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.config.max_release_bytes:
                        raise RuntimeError("Release Edge trop volumineuse")
                    if content_length and int(content_length) != expected_size:
                        raise RuntimeError("Content-Length de release différent du manifeste signé")
                    with tmp_path.open("wb") as handle:
                        for chunk in response.iter_bytes(1024 * 1024):
                            if not chunk:
                                continue
                            total += len(chunk)
                            if total > self.config.max_release_bytes or total > expected_size:
                                raise RuntimeError("Taille de release Edge supérieure au manifeste")
                            digest.update(chunk)
                            handle.write(chunk)
                        handle.flush()
                        os.fsync(handle.fileno())
                    return digest.hexdigest(), total
        raise RuntimeError("Téléchargement de release Edge non finalisé")

    def stage(self, offer: dict[str, Any]) -> dict[str, Any]:
        if not offer.get("update_available"):
            return {"staged": False, "reason": "no_update"}
        bundle = offer.get("release")
        if not isinstance(bundle, dict) or not self.central.verify_release_bundle(bundle):
            raise RuntimeError("Signature centrale de release Edge invalide")

        manifest = bundle.get("manifest")
        if not isinstance(manifest, dict) or manifest.get("kind") != "center_edge_release_manifest_v1":
            raise RuntimeError("Manifeste de release Edge invalide")
        release_id = str(bundle.get("release_id") or manifest.get("release_id") or "")
        if not release_id or release_id != str(manifest.get("release_id") or ""):
            raise RuntimeError("Identifiant de release Edge incohérent")
        if offer.get("action") != "rollback" and not _meets_minimum(
            self.config.software_version,
            str(manifest.get("min_current_version") or "") or None,
        ):
            raise RuntimeError(
                "Release Edge incompatible avec la version actuellement installée ; mise à niveau intermédiaire requise"
            )

        artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
        if artifact.get("format") != "tar.gz":
            raise RuntimeError("Format de release Edge non supporté")
        url = self._validate_artifact_url(str(artifact.get("url") or ""))
        expected_sha = str(artifact.get("sha256") or "").strip().lower()
        expected_size = int(artifact.get("size_bytes") or 0)
        if len(expected_sha) != 64 or expected_size <= 0 or expected_size > self.config.max_release_bytes:
            raise RuntimeError("Empreinte ou taille de release Edge invalide")

        final_path = self.root / f"{release_id}.tar.gz"
        tmp_path = self.root / f".download-{release_id}.tmp"
        try:
            actual_sha, total = self._download_verified(url, tmp_path, expected_size)
            if total != expected_size:
                raise RuntimeError(f"Taille de release Edge incohérente : {total} != {expected_size}")
            if actual_sha != expected_sha:
                raise RuntimeError("SHA-256 de release Edge différent du manifeste signé")
            os.replace(tmp_path, final_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

        # P9 conserve la preuve signée complète pour que l'updater root puisse
        # refaire sa propre vérification depuis un trust store qu'un daemon
        # compromis ne peut pas modifier.
        state = {
            "release_id": release_id,
            "action": str(offer.get("action") or "install"),
            "source_release_id": offer.get("source_release_id"),
            "software_version": str(manifest.get("software_version") or ""),
            "artifact_sha256": expected_sha,
            "artifact_size_bytes": expected_size,
            "artifact_path": str(final_path.resolve()),
            "manifest": manifest,
            "manifest_hash": bundle.get("manifest_hash"),
            "manifest_signature_b64": bundle.get("manifest_signature_b64"),
            "signing_key_id": bundle.get("signing_key_id"),
            "verified": True,
        }
        self._write_json_atomic(self.staged_state_path, state)
        self.central.attest_release(
            release_id=release_id,
            software_version=state["software_version"],
            result="staged",
            artifact_sha256=expected_sha,
        )
        return {"staged": True, **state}

    def status(self) -> dict[str, Any]:
        staged: dict[str, Any] | None = None
        receipt: dict[str, Any] | None = None
        if self.staged_state_path.exists():
            try:
                staged = json.loads(self.staged_state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                staged = {"corrupt": True}
        if self.install_receipt_path.exists():
            try:
                receipt = json.loads(self.install_receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                receipt = {"corrupt": True}
        return {"staged": staged, "install_receipt": receipt}

    def attest_install_receipt(self) -> dict[str, Any]:
        if not self.install_receipt_path.exists():
            raise RuntimeError("Aucun reçu d'installation Edge à attester")
        try:
            receipt = json.loads(self.install_receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Reçu d'installation Edge illisible") from exc
        result = str(receipt.get("result") or "")
        if result not in {"installed", "failed", "rolled_back"}:
            raise RuntimeError("Reçu d'installation Edge invalide")
        receipt_version = str(receipt.get("software_version") or "").strip()
        if result in {"installed", "rolled_back"} and receipt_version != self.config.software_version:
            raise RuntimeError(
                "Attestation refusée : le daemon en cours d'exécution ne correspond pas encore à la version du reçu. "
                f"running={self.config.software_version} receipt={receipt_version}"
            )
        response = self.central.attest_release(
            release_id=str(receipt["release_id"]),
            software_version=receipt_version,
            result=result,
            artifact_sha256=str(receipt["artifact_sha256"]),
        )
        archived = self.root / f"install-receipt-{receipt['release_id']}-{result}.json"
        os.replace(self.install_receipt_path, archived)
        return {**response, "receipt_archived": str(archived)}

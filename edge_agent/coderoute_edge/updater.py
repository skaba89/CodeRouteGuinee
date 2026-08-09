from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
from pathlib import Path
from typing import Any

_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_MAX_ARCHIVE_MEMBERS = 20_000


def _json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Fichier de release Edge illisible : {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Fichier de release Edge invalide : {path}")
    return data


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), total


def _safe_extract(archive: Path, destination: Path, *, max_bytes: int) -> None:
    total = 0
    with tarfile.open(archive, mode="r:gz") as tar:
        members = tar.getmembers()
        if not members or len(members) > _MAX_ARCHIVE_MEMBERS:
            raise RuntimeError("Archive Edge vide ou contenant trop de fichiers")
        destination_resolved = destination.resolve()
        for member in members:
            name = member.name.replace("\\", "/")
            if name.startswith("/") or any(part in {"", ".."} for part in Path(name).parts):
                raise RuntimeError("Archive Edge contient un chemin interdit")
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise RuntimeError("Archive Edge contient un lien ou périphérique interdit")
            total += max(0, int(member.size or 0))
            if total > max_bytes * 4:
                raise RuntimeError("Archive Edge décompressée anormalement volumineuse")
            target = (destination / name).resolve()
            if destination_resolved not in target.parents and target != destination_resolved:
                raise RuntimeError("Archive Edge tente une sortie du répertoire de release")
        tar.extractall(destination, members=members, filter="data")


def _validate_layout(root: Path) -> None:
    package = root / "edge_agent" / "coderoute_edge"
    requirements = root / "edge_agent" / "requirements.txt"
    if not package.is_dir() or not (package / "__init__.py").is_file() or not requirements.is_file():
        raise RuntimeError(
            "Archive Edge invalide : edge_agent/coderoute_edge et edge_agent/requirements.txt sont obligatoires"
        )


def _assert_managed_target(target: Path, versions: Path) -> Path:
    resolved = target.resolve()
    root = versions.resolve()
    if resolved == root or root not in resolved.parents:
        raise RuntimeError("Lien de version Edge hors du répertoire géré")
    if not resolved.is_dir():
        raise RuntimeError("Version Edge gérée introuvable")
    return resolved


def _resolve_managed_link(link: Path, versions: Path) -> Path | None:
    if not link.exists() and not link.is_symlink():
        return None
    if not link.is_symlink():
        raise RuntimeError(f"{link.name} Edge doit être un lien symbolique géré")
    raw = os.readlink(link)
    return _assert_managed_target(link.parent / raw, versions)


def _switch_link(link: Path, target: Path, versions: Path) -> None:
    managed_target = _assert_managed_target(target, versions)
    temp = link.with_name(link.name + ".next")
    temp.unlink(missing_ok=True)
    relative = os.path.relpath(managed_target, start=link.parent)
    temp.symlink_to(relative, target_is_directory=True)
    os.replace(temp, link)


def apply_verified_release(release_root: Path) -> dict[str, Any]:
    release_root.mkdir(parents=True, exist_ok=True)
    staged_path = release_root / "staged.json"
    staged = _load_json(staged_path)
    if staged.get("verified") is not True:
        raise RuntimeError("La release Edge n'a pas été marquée comme vérifiée")

    release_id = str(staged.get("release_id") or "")
    version = str(staged.get("software_version") or "")
    if not release_id or not _VERSION_RE.fullmatch(version):
        raise RuntimeError("Identité ou version de release Edge invalide")
    artifact = Path(str(staged.get("artifact_path") or ""))
    if not artifact.is_file():
        raise RuntimeError("Artefact Edge vérifié introuvable")

    actual_sha, actual_size = _hash_file(artifact)
    expected_sha = str(staged.get("artifact_sha256") or "").lower()
    expected_size = int(staged.get("artifact_size_bytes") or 0)
    if actual_sha != expected_sha or actual_size != expected_size:
        raise RuntimeError("Artefact Edge modifié après staging")

    versions = release_root / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    target = versions / version
    install_tmp = versions / f".install-{release_id}"
    if install_tmp.exists():
        shutil.rmtree(install_tmp)
    install_tmp.mkdir(parents=True)
    try:
        _safe_extract(artifact, install_tmp, max_bytes=max(expected_size, 1))
        _validate_layout(install_tmp)
        _json_atomic(install_tmp / ".release-state.json", staged)
        if target.exists():
            managed_target = _assert_managed_target(target, versions)
            existing = _load_json(managed_target / ".release-state.json")
            if existing.get("artifact_sha256") != expected_sha:
                raise RuntimeError("Une version Edge existe déjà avec un autre artefact")
            shutil.rmtree(install_tmp)
        else:
            os.replace(install_tmp, target)
    except Exception:
        if install_tmp.exists():
            shutil.rmtree(install_tmp)
        raise

    target = _assert_managed_target(target, versions)
    current = release_root / "current"
    previous = release_root / "previous"
    old_target = _resolve_managed_link(current, versions)
    if old_target and old_target != target:
        _switch_link(previous, old_target, versions)
    _switch_link(current, target, versions)

    result = "rolled_back" if staged.get("action") == "rollback" else "installed"
    receipt = {
        "release_id": release_id,
        "software_version": version,
        "artifact_sha256": expected_sha,
        "result": result,
        "current_path": str(target),
        "previous_path": str(old_target) if old_target else None,
    }
    _json_atomic(release_root / "install-receipt.json", receipt)
    return receipt


def rollback_to_previous(release_root: Path) -> dict[str, Any]:
    versions = release_root / "versions"
    current = release_root / "current"
    previous = release_root / "previous"
    current_target = _resolve_managed_link(current, versions)
    previous_target = _resolve_managed_link(previous, versions)
    if current_target is None or previous_target is None:
        raise RuntimeError("Aucune version Edge précédente disponible pour rollback")
    previous_state = _load_json(previous_target / ".release-state.json")
    _switch_link(current, previous_target, versions)
    _switch_link(previous, current_target, versions)
    receipt = {
        "release_id": str(previous_state["release_id"]),
        "software_version": str(previous_state["software_version"]),
        "artifact_sha256": str(previous_state["artifact_sha256"]),
        "result": "rolled_back",
        "current_path": str(previous_target),
        "previous_path": str(current_target),
    }
    _json_atomic(release_root / "install-receipt.json", receipt)
    return receipt

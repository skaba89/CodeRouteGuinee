from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from pathlib import Path
from uuid import uuid4

import pytest

from coderoute_edge.updater import apply_verified_release, rollback_to_previous


def _tar_bytes(version: str, *, malicious: str | None = None, symlink: bool = False) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        if malicious:
            info = tarfile.TarInfo(malicious)
            data = b"escape"
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        else:
            if symlink:
                info = tarfile.TarInfo("edge_agent/coderoute_edge/evil-link")
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                tar.addfile(info)
            files = {
                "edge_agent/coderoute_edge/__init__.py": f"__version__ = {version!r}\n".encode(),
                "edge_agent/coderoute_edge/app.py": b"# release test\n",
                "edge_agent/requirements.txt": b"fastapi==0.115.6\n",
            }
            for name, data in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _stage(root: Path, version: str, payload: bytes, *, action: str = "install") -> dict:
    root.mkdir(parents=True, exist_ok=True)
    release_id = str(uuid4())
    artifact = root / f"{release_id}.tar.gz"
    artifact.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    state = {
        "release_id": release_id,
        "action": action,
        "source_release_id": None,
        "software_version": version,
        "artifact_sha256": sha,
        "artifact_size_bytes": len(payload),
        "artifact_path": str(artifact.resolve()),
        "manifest_hash": "m" * 64,
        "signing_key_id": "edge-release-v1:test",
        "verified": True,
    }
    (root / "staged.json").write_text(json.dumps(state), encoding="utf-8")
    return state


def _link_target(link: Path) -> Path:
    return (link.parent / os.readlink(link)).resolve()


def test_updater_installs_atomically_and_rolls_back(tmp_path: Path) -> None:
    root = tmp_path / "releases"
    first = _stage(root, "edge-agent-0.3.0", _tar_bytes("edge-agent-0.3.0"))
    receipt1 = apply_verified_release(root)
    assert receipt1["result"] == "installed"
    current1 = _link_target(root / "current")
    assert current1.name == "edge-agent-0.3.0"
    assert json.loads((current1 / ".release-state.json").read_text())["release_id"] == first["release_id"]

    second = _stage(root, "edge-agent-0.3.1", _tar_bytes("edge-agent-0.3.1"))
    receipt2 = apply_verified_release(root)
    assert receipt2["result"] == "installed"
    assert _link_target(root / "current").name == "edge-agent-0.3.1"
    assert _link_target(root / "previous").name == "edge-agent-0.3.0"

    rollback = rollback_to_previous(root)
    assert rollback["result"] == "rolled_back"
    assert rollback["release_id"] == first["release_id"]
    assert _link_target(root / "current").name == "edge-agent-0.3.0"
    assert _link_target(root / "previous").name == "edge-agent-0.3.1"
    assert second["release_id"] != first["release_id"]


def test_updater_rejects_artifact_changed_after_staging(tmp_path: Path) -> None:
    root = tmp_path / "releases"
    state = _stage(root, "edge-agent-0.3.1", _tar_bytes("edge-agent-0.3.1"))
    Path(state["artifact_path"]).write_bytes(b"tampered-after-verification")
    with pytest.raises(RuntimeError, match="modifié après staging"):
        apply_verified_release(root)


def test_updater_rejects_path_traversal_and_symlink_members(tmp_path: Path) -> None:
    traversal_root = tmp_path / "traversal"
    _stage(traversal_root, "edge-agent-0.3.1", _tar_bytes("edge-agent-0.3.1", malicious="../escape"))
    with pytest.raises(RuntimeError, match="chemin interdit"):
        apply_verified_release(traversal_root)
    assert not (tmp_path / "escape").exists()

    symlink_root = tmp_path / "symlink"
    _stage(symlink_root, "edge-agent-0.3.1", _tar_bytes("edge-agent-0.3.1", symlink=True))
    with pytest.raises(RuntimeError, match="lien ou périphérique interdit"):
        apply_verified_release(symlink_root)


def test_updater_refuses_manipulated_current_link_outside_versions(tmp_path: Path) -> None:
    root = tmp_path / "releases"
    _stage(root, "edge-agent-0.3.0", _tar_bytes("edge-agent-0.3.0"))
    apply_verified_release(root)

    outside = tmp_path / "outside-version"
    outside.mkdir()
    current = root / "current"
    current.unlink()
    current.symlink_to(outside, target_is_directory=True)

    _stage(root, "edge-agent-0.3.1", _tar_bytes("edge-agent-0.3.1"))
    with pytest.raises(RuntimeError, match="hors du répertoire géré"):
        apply_verified_release(root)

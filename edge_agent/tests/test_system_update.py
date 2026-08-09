from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import tarfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from coderoute_edge.system_update import apply_system_update_transaction
from coderoute_edge.updater import apply_verified_release


def _archive(version: str) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        files = {
            "edge_agent/coderoute_edge/__init__.py": f"__version__={version!r}\n".encode(),
            "edge_agent/coderoute_edge/app.py": b"# app\n",
            "edge_agent/requirements.txt": b"fastapi==0.115.6\n",
        }
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _stage(root: Path, version: str) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    payload = _archive(version)
    release_id = str(uuid4())
    artifact = root / f"{release_id}.tar.gz"
    artifact.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    state = {
        "release_id": release_id,
        "action": "install",
        "software_version": version,
        "artifact_sha256": sha,
        "artifact_size_bytes": len(payload),
        "artifact_path": str(artifact.resolve()),
        "verified": True,
    }
    (root / "staged.json").write_text(json.dumps(state), encoding="utf-8")
    return state


def _db(path: Path, statuses: list[str] | None = None) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE leases(attempt_id TEXT PRIMARY KEY,status TEXT NOT NULL)")
        for index, status in enumerate(statuses or []):
            conn.execute("INSERT INTO leases(attempt_id,status) VALUES(?,?)", (f"a-{index}", status))
        conn.commit()


def _config(tmp_path: Path, database: Path) -> SimpleNamespace:
    return SimpleNamespace(
        database_path=database,
        maintenance_windows="sun@01:00-04:00",
        maintenance_timezone="Africa/Conakry",
        release_dir=tmp_path / "releases",
        runtime_python="/usr/bin/python3",
        systemd_service_name="coderoute-edge.service",
        public_url="https://edge.example.test:8443",
        healthcheck_timeout_seconds=30,
        healthcheck_ca_path=None,
    )


def _runtime(_root: Path, python: str) -> dict:
    return {"python": python, "requirements_lock_sha256": "f" * 64, "wheel_count": 12}


def _current_target(root: Path) -> Path:
    link = root / "current"
    return (link.parent / os.readlink(link)).resolve()


def test_system_update_confirms_exact_running_version(tmp_path: Path) -> None:
    database = tmp_path / "edge.db"
    _db(database)
    config = _config(tmp_path, database)
    _stage(config.release_dir, "edge-agent-0.3.0")
    apply_verified_release(config.release_dir)
    _stage(config.release_dir, "edge-agent-0.4.0")
    restarts: list[str] = []

    result = apply_system_update_transaction(
        config,
        emergency_window_bypass=True,
        restart_service=lambda service: restarts.append(service),
        health_probe=lambda *_args: {"status": "ok", "software_version": "edge-agent-0.4.0"},
        runtime_prepare=_runtime,
    )

    assert result["ok"] is True
    assert result["phase"] == "confirmed"
    assert restarts == ["coderoute-edge.service"]
    assert _current_target(config.release_dir).name == "edge-agent-0.4.0"
    receipt = json.loads((config.release_dir / "install-receipt.json").read_text())
    assert receipt["result"] == "installed"


def test_health_version_mismatch_rolls_back_and_marks_bad_release_failed(tmp_path: Path) -> None:
    database = tmp_path / "edge.db"
    _db(database)
    config = _config(tmp_path, database)
    previous = _stage(config.release_dir, "edge-agent-0.3.0")
    apply_verified_release(config.release_dir)
    bad = _stage(config.release_dir, "edge-agent-0.4.0")
    restarts: list[str] = []
    probes = iter([
        {"status": "ok", "software_version": "edge-agent-0.3.0"},
        {"status": "ok", "software_version": "edge-agent-0.3.0"},
    ])

    result = apply_system_update_transaction(
        config,
        emergency_window_bypass=True,
        restart_service=lambda service: restarts.append(service),
        health_probe=lambda *_args: next(probes),
        runtime_prepare=_runtime,
    )

    assert result["ok"] is False
    assert result["phase"] == "rolled_back"
    assert len(restarts) == 2
    assert _current_target(config.release_dir).name == "edge-agent-0.3.0"
    receipt = json.loads((config.release_dir / "install-receipt.json").read_text())
    assert receipt["result"] == "failed"
    assert receipt["release_id"] == bad["release_id"]
    assert receipt["rollback_confirmed"] is True
    assert receipt["rollback_release_id"] == previous["release_id"]


def test_active_exam_blocks_transaction_before_link_switch_or_restart(tmp_path: Path) -> None:
    database = tmp_path / "edge.db"
    _db(database, ["active"])
    config = _config(tmp_path, database)
    _stage(config.release_dir, "edge-agent-0.3.0")
    apply_verified_release(config.release_dir)
    before = _current_target(config.release_dir)
    _stage(config.release_dir, "edge-agent-0.4.0")
    restarts: list[str] = []

    with pytest.raises(RuntimeError, match="examen"):
        apply_system_update_transaction(
            config,
            emergency_window_bypass=True,
            restart_service=lambda service: restarts.append(service),
            health_probe=lambda *_args: {"status": "ok", "software_version": "edge-agent-0.4.0"},
            runtime_prepare=_runtime,
        )

    assert restarts == []
    assert _current_target(config.release_dir) == before

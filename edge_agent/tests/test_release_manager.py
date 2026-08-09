from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from coderoute_edge.release import EdgeReleaseManager


class FakeCentral:
    def __init__(self, *, signature_ok: bool = True):
        self.signature_ok = signature_ok
        self.attestations: list[dict] = []

    def check_release(self, _current_version: str) -> dict:
        return {"update_available": False, "action": "none"}

    def verify_release_bundle(self, _bundle: dict) -> bool:
        return self.signature_ok

    def attest_release(self, **kwargs) -> dict:
        self.attestations.append(kwargs)
        return {"accepted": True}


def _config(tmp_path: Path, version: str = "edge-agent-0.3.0") -> SimpleNamespace:
    return SimpleNamespace(
        release_dir=tmp_path / "releases",
        software_version=version,
        max_release_bytes=10 * 1024 * 1024,
    )


def _offer(payload: bytes, *, minimum: str | None = "edge-agent-0.3.0") -> dict:
    sha = hashlib.sha256(payload).hexdigest()
    return {
        "update_available": True,
        "action": "install",
        "release": {
            "release_id": "release-p8-test",
            "manifest": {
                "kind": "center_edge_release_manifest_v1",
                "version": 1,
                "release_id": "release-p8-test",
                "software_version": "edge-agent-0.3.1",
                "artifact": {
                    "format": "tar.gz",
                    "url": "https://releases.coderoute.gov.gn/edge-agent-0.3.1.tar.gz",
                    "sha256": sha,
                    "size_bytes": len(payload),
                },
                "created_at": "2026-08-09T00:00:00Z",
                "min_current_version": minimum,
                "release_notes": "test",
            },
            "manifest_hash": "d" * 64,
            "manifest_signature_b64": "signature",
            "signing_key_id": "edge-release-v1:test",
        },
    }


def _inject_download(manager: EdgeReleaseManager, payload: bytes, *, sha_override: str | None = None) -> None:
    def fake_download(self, _url: str, tmp_path: Path, _expected_size: int):
        tmp_path.write_bytes(payload)
        return sha_override or hashlib.sha256(payload).hexdigest(), len(payload)

    manager._download_verified = MethodType(fake_download, manager)  # type: ignore[method-assign]


def test_stage_rejects_invalid_signature_and_incompatible_minimum(tmp_path: Path) -> None:
    payload = b"verified release bytes"
    invalid = EdgeReleaseManager(_config(tmp_path), FakeCentral(signature_ok=False))
    with pytest.raises(RuntimeError, match="Signature centrale"):
        invalid.stage(_offer(payload))

    incompatible = EdgeReleaseManager(_config(tmp_path, "edge-agent-0.2.9"), FakeCentral())
    with pytest.raises(RuntimeError, match="mise à niveau intermédiaire"):
        incompatible.stage(_offer(payload, minimum="edge-agent-0.3.0"))


def test_stage_writes_only_verified_artifact_and_attests(tmp_path: Path) -> None:
    payload = b"verified release bytes"
    central = FakeCentral()
    manager = EdgeReleaseManager(_config(tmp_path), central)
    _inject_download(manager, payload)

    result = manager.stage(_offer(payload))
    assert result["staged"] is True
    assert Path(result["artifact_path"]).read_bytes() == payload
    assert manager.staged_state_path.exists()
    assert central.attestations == [{
        "release_id": "release-p8-test",
        "software_version": "edge-agent-0.3.1",
        "result": "staged",
        "artifact_sha256": hashlib.sha256(payload).hexdigest(),
    }]


def test_stage_deletes_temporary_artifact_when_sha_mismatches(tmp_path: Path) -> None:
    payload = b"verified release bytes"
    manager = EdgeReleaseManager(_config(tmp_path), FakeCentral())
    _inject_download(manager, payload, sha_override="0" * 64)

    with pytest.raises(RuntimeError, match="SHA-256"):
        manager.stage(_offer(payload))
    assert not any(path.name.startswith(".download-") for path in manager.root.iterdir())
    assert not manager.staged_state_path.exists()


def test_no_update_does_not_touch_disk(tmp_path: Path) -> None:
    manager = EdgeReleaseManager(_config(tmp_path), FakeCentral())
    result = manager.stage({"update_available": False, "action": "none"})
    assert result == {"staged": False, "reason": "no_update"}
    assert not manager.staged_state_path.exists()


def test_install_receipt_requires_matching_running_daemon_before_attestation(tmp_path: Path) -> None:
    receipt = {
        "release_id": "release-installed-p8",
        "software_version": "edge-agent-0.3.1",
        "artifact_sha256": "a" * 64,
        "result": "installed",
    }

    old_central = FakeCentral()
    old_manager = EdgeReleaseManager(_config(tmp_path, "edge-agent-0.3.0"), old_central)
    old_manager.root.mkdir(parents=True, exist_ok=True)
    old_manager.install_receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(RuntimeError, match="daemon en cours"):
        old_manager.attest_install_receipt()
    assert old_central.attestations == []
    assert old_manager.install_receipt_path.exists()

    new_central = FakeCentral()
    new_manager = EdgeReleaseManager(_config(tmp_path, "edge-agent-0.3.1"), new_central)
    result = new_manager.attest_install_receipt()
    assert result["accepted"] is True
    assert new_central.attestations == [{
        "release_id": "release-installed-p8",
        "software_version": "edge-agent-0.3.1",
        "result": "installed",
        "artifact_sha256": "a" * 64,
    }]
    assert not new_manager.install_receipt_path.exists()
    assert Path(result["receipt_archived"]).exists()

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coderoute_edge.crypto import b64url, canonical_json, sha256_hex, sign_payload
from coderoute_edge.release_trust import verify_staged_release_for_root


def _signed_stage(tmp_path: Path) -> tuple[dict, Path]:
    root = tmp_path / "releases"
    root.mkdir(parents=True)
    private = Ed25519PrivateKey.generate()
    public = b64url(private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ))
    key_id = "edge-release-v1:test-root"
    release_id = "release-root-trust-001"
    sha = "a" * 64
    manifest = {
        "kind": "center_edge_release_manifest_v1",
        "version": 2,
        "release_id": release_id,
        "software_version": "edge-agent-0.4.0",
        "artifact": {
            "format": "tar.gz",
            "url": "https://releases.coderoute.gov.gn/edge-agent-0.4.0.tar.gz",
            "sha256": sha,
            "size_bytes": 1234,
        },
        "created_at": "2026-08-09T05:00:00Z",
        "min_current_version": "edge-agent-0.3.0",
        "release_notes": "P9",
        "supply_chain": {
            "builder": "github-actions",
            "source_commit_sha": "1" * 40,
            "workflow_ref": "Edge Release Supply Chain@refs/tags/edge-agent-0.4.0",
            "provenance_url": "https://github.com/skaba89/CodeRouteGuinee/attestations/1",
            "sbom_sha256": "b" * 64,
            "sbom_attestation_url": "https://github.com/skaba89/CodeRouteGuinee/attestations/2",
            "subject_sha256": sha,
            "vulnerability_scan_status": "passed",
        },
    }
    artifact = root / f"{release_id}.tar.gz"
    artifact.write_bytes(b"not-read-by-trust-test")
    staged = {
        "release_id": release_id,
        "action": "install",
        "software_version": "edge-agent-0.4.0",
        "artifact_sha256": sha,
        "artifact_size_bytes": 1234,
        "artifact_path": str(artifact.resolve()),
        "manifest": manifest,
        "manifest_hash": sha256_hex(canonical_json(manifest)),
        "manifest_signature_b64": sign_payload(private, manifest),
        "signing_key_id": key_id,
        "verified": True,
    }
    trust = tmp_path / "release-trust.json"
    trust.write_text(json.dumps({"trusted_keys": [{"key_id": key_id, "public_key_b64": public, "active": True}]}), encoding="utf-8")
    trust.chmod(0o644)
    return staged, trust


def test_root_trust_accepts_matching_signed_p9_stage(tmp_path: Path) -> None:
    staged, trust = _signed_stage(tmp_path)
    verified = verify_staged_release_for_root(staged, release_root=tmp_path / "releases", trust_store_path=trust)
    assert verified["release_id"] == staged["release_id"]
    assert verified["software_version"] == "edge-agent-0.4.0"
    assert verified["signing_key_id"] == "edge-release-v1:test-root"


def test_root_trust_rejects_manifest_tampered_after_daemon_verification(tmp_path: Path) -> None:
    staged, trust = _signed_stage(tmp_path)
    staged["manifest"]["software_version"] = "edge-agent-9.9.9"
    staged["software_version"] = "edge-agent-9.9.9"
    staged["manifest_hash"] = sha256_hex(canonical_json(staged["manifest"]))
    with pytest.raises(RuntimeError, match="Signature Ed25519"):
        verify_staged_release_for_root(staged, release_root=tmp_path / "releases", trust_store_path=trust)


def test_root_trust_rejects_untrusted_key_and_writable_trust_store(tmp_path: Path) -> None:
    staged, trust = _signed_stage(tmp_path)
    trust.write_text(json.dumps({"trusted_keys": [{"key_id": "other", "public_key_b64": "x"}]}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="non approuvée"):
        verify_staged_release_for_root(staged, release_root=tmp_path / "releases", trust_store_path=trust)

    staged, trust = _signed_stage(tmp_path / "second")
    trust.chmod(0o666)
    with pytest.raises(RuntimeError, match="insécurisé"):
        verify_staged_release_for_root(staged, release_root=tmp_path / "second" / "releases", trust_store_path=trust)

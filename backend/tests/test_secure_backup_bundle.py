import base64
import hashlib
import json
import os
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from scripts import secure_backup_bundle


def _prepare(tmp_path: Path) -> tuple[Path, Path]:
    dump = tmp_path / "coderoute.dump"
    dump.write_bytes((b"CodeRoute-PRA\x00" * 10000) + os.urandom(1024))
    digest = hashlib.sha256(dump.read_bytes()).hexdigest()
    manifest = tmp_path / "coderoute.manifest.json"
    manifest.write_text(
        json.dumps({
            "kind": "coderoute_postgres_backup_v1",
            "created_at": "2026-08-09T10:00:00+00:00",
            "dump_file": dump.name,
            "format": "pg_dump_custom",
            "sha256": digest,
            "size_bytes": dump.stat().st_size,
            "alembic_version": "test-head",
        }),
        encoding="utf-8",
    )
    return dump, manifest


def _set_key(monkeypatch, byte: bytes = b"k") -> None:
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY_B64", base64.b64encode(byte * 32).decode())
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY_ID", "backup-key-test")


def test_secure_bundle_round_trip(monkeypatch, tmp_path: Path) -> None:
    _set_key(monkeypatch)
    dump, manifest = _prepare(tmp_path)
    original = dump.read_bytes()
    bundle = tmp_path / "coderoute.crgbak"

    packed = secure_backup_bundle.pack(dump, manifest, bundle)
    out = tmp_path / "restore"
    unpacked = secure_backup_bundle.unpack(bundle, out)

    assert packed["kind"] == "coderoute_secure_backup_v2"
    assert packed["key_id"] == "backup-key-test"
    assert unpacked["dump_sha256"] == hashlib.sha256(original).hexdigest()
    assert (out / "coderoute-restored.dump").read_bytes() == original
    assert json.loads((out / "coderoute-restored.manifest.json").read_text())["kind"] == "coderoute_postgres_backup_v1"


def test_tampered_ciphertext_is_rejected(monkeypatch, tmp_path: Path) -> None:
    _set_key(monkeypatch)
    dump, manifest = _prepare(tmp_path)
    bundle = tmp_path / "coderoute.crgbak"
    secure_backup_bundle.pack(dump, manifest, bundle)

    raw = bytearray(bundle.read_bytes())
    raw[len(raw) // 2] ^= 0x01
    bundle.write_bytes(raw)

    with pytest.raises(InvalidTag):
        secure_backup_bundle.unpack(bundle, tmp_path / "restore")
    assert not (tmp_path / "restore" / "coderoute-restored.dump").exists()


def test_wrong_key_is_rejected(monkeypatch, tmp_path: Path) -> None:
    _set_key(monkeypatch, b"a")
    dump, manifest = _prepare(tmp_path)
    bundle = tmp_path / "coderoute.crgbak"
    secure_backup_bundle.pack(dump, manifest, bundle)

    _set_key(monkeypatch, b"b")
    with pytest.raises(InvalidTag):
        secure_backup_bundle.unpack(bundle, tmp_path / "restore")


def test_key_id_mismatch_is_rejected_before_publish(monkeypatch, tmp_path: Path) -> None:
    _set_key(monkeypatch)
    dump, manifest = _prepare(tmp_path)
    bundle = tmp_path / "coderoute.crgbak"
    secure_backup_bundle.pack(dump, manifest, bundle)

    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY_ID", "different-key-id")
    with pytest.raises(SystemExit, match="KEY_ID"):
        secure_backup_bundle.unpack(bundle, tmp_path / "restore")


def test_pack_rejects_dump_manifest_mismatch(monkeypatch, tmp_path: Path) -> None:
    _set_key(monkeypatch)
    dump, manifest = _prepare(tmp_path)
    dump.write_bytes(dump.read_bytes() + b"tampered")
    with pytest.raises(SystemExit, match="ne correspond pas"):
        secure_backup_bundle.pack(dump, manifest, tmp_path / "coderoute.crgbak")

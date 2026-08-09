#!/usr/bin/env python3
"""Créer/déballer un backup CodeRoute chiffré AES-256-GCM.

Format CRGBAK2 :
  magic | header_len | header_json(AAD) | nonce | ciphertext | tag

Le payload chiffré contient le manifest P10 puis le pg_dump. Le fichier clair
n'est publié dans le dossier de restore qu'après validation du tag GCM.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import struct
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"CRGBAK2\n"
NONCE_SIZE = 12
TAG_SIZE = 16
CHUNK = 1024 * 1024


def _key() -> bytes:
    raw = os.getenv("BACKUP_ENCRYPTION_KEY_B64", "").strip()
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise SystemExit("BACKUP_ENCRYPTION_KEY_B64 invalide") from exc
    if len(key) != 32:
        raise SystemExit("BACKUP_ENCRYPTION_KEY_B64 doit décoder exactement 32 octets")
    return key


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("kind") != "coderoute_postgres_backup_v1":
        raise SystemExit("manifest backup invalide")
    return payload


def pack(dump: Path, manifest: Path, output: Path) -> dict:
    if not dump.is_file() or not manifest.is_file():
        raise SystemExit("dump/manifest introuvable")
    manifest_payload = _load_manifest(manifest)
    dump_sha = _sha256(dump)
    dump_size = dump.stat().st_size
    if manifest_payload.get("sha256") != dump_sha or int(manifest_payload.get("size_bytes", -1)) != dump_size:
        raise SystemExit("le dump ne correspond pas au manifest")

    manifest_bytes = manifest.read_bytes()
    header = {
        "kind": "coderoute_secure_backup_v2",
        "cipher": "AES-256-GCM",
        "created_at": datetime.now(UTC).isoformat(),
        "key_id": os.getenv("BACKUP_ENCRYPTION_KEY_ID", "").strip() or "unversioned",
        "dump_sha256": dump_sha,
        "dump_size_bytes": dump_size,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(header_bytes) > 64 * 1024:
        raise SystemExit("header backup trop volumineux")

    output.parent.mkdir(parents=True, exist_ok=True)
    nonce = os.urandom(NONCE_SIZE)
    encryptor = Cipher(algorithms.AES(_key()), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(header_bytes)

    tmp = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("wb") as target:
            target.write(MAGIC)
            target.write(struct.pack(">I", len(header_bytes)))
            target.write(header_bytes)
            target.write(nonce)
            target.write(encryptor.update(struct.pack(">Q", len(manifest_bytes))))
            target.write(encryptor.update(manifest_bytes))
            with dump.open("rb") as source:
                while chunk := source.read(CHUNK):
                    target.write(encryptor.update(chunk))
            target.write(encryptor.finalize())
            target.write(encryptor.tag)
        os.chmod(tmp, 0o600)
        os.replace(tmp, output)
    finally:
        tmp.unlink(missing_ok=True)

    result = {
        **header,
        "bundle_file": output.name,
        "bundle_sha256": _sha256(output),
        "bundle_size_bytes": output.stat().st_size,
    }
    return result


def unpack(bundle: Path, output_dir: Path) -> dict:
    if not bundle.is_file():
        raise SystemExit("bundle introuvable")
    output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)

    total_size = bundle.stat().st_size
    with bundle.open("rb") as source:
        if source.read(len(MAGIC)) != MAGIC:
            raise SystemExit("format backup sécurisé invalide")
        raw_len = source.read(4)
        if len(raw_len) != 4:
            raise SystemExit("header backup tronqué")
        header_len = struct.unpack(">I", raw_len)[0]
        if header_len <= 0 or header_len > 64 * 1024:
            raise SystemExit("taille header backup invalide")
        header_bytes = source.read(header_len)
        nonce = source.read(NONCE_SIZE)
        if len(header_bytes) != header_len or len(nonce) != NONCE_SIZE:
            raise SystemExit("backup sécurisé tronqué")
        header = json.loads(header_bytes)
        if header.get("kind") != "coderoute_secure_backup_v2" or header.get("cipher") != "AES-256-GCM":
            raise SystemExit("header backup sécurisé invalide")

        expected_key_id = os.getenv("BACKUP_ENCRYPTION_KEY_ID", "").strip()
        if expected_key_id and header.get("key_id") != expected_key_id:
            raise SystemExit("BACKUP_ENCRYPTION_KEY_ID ne correspond pas au bundle")

        ciphertext_start = source.tell()
        ciphertext_len = total_size - ciphertext_start - TAG_SIZE
        if ciphertext_len <= 8:
            raise SystemExit("ciphertext backup invalide")
        source.seek(total_size - TAG_SIZE)
        tag = source.read(TAG_SIZE)
        source.seek(ciphertext_start)

        decryptor = Cipher(algorithms.AES(_key()), modes.GCM(nonce, tag)).decryptor()
        decryptor.authenticate_additional_data(header_bytes)

        fd, temp_name = tempfile.mkstemp(prefix=".coderoute-restore-", dir=output_dir)
        os.close(fd)
        temp_payload = Path(temp_name)
        try:
            remaining = ciphertext_len
            with temp_payload.open("wb") as clear:
                while remaining:
                    chunk = source.read(min(CHUNK, remaining))
                    if not chunk:
                        raise SystemExit("ciphertext backup tronqué")
                    remaining -= len(chunk)
                    clear.write(decryptor.update(chunk))
                clear.write(decryptor.finalize())
            os.chmod(temp_payload, 0o600)

            with temp_payload.open("rb") as clear:
                raw_manifest_len = clear.read(8)
                if len(raw_manifest_len) != 8:
                    raise SystemExit("payload backup invalide")
                manifest_len = struct.unpack(">Q", raw_manifest_len)[0]
                if manifest_len <= 0 or manifest_len > 16 * 1024 * 1024:
                    raise SystemExit("manifest chiffré invalide")
                manifest_bytes = clear.read(manifest_len)
                if len(manifest_bytes) != manifest_len:
                    raise SystemExit("manifest chiffré tronqué")

                if hashlib.sha256(manifest_bytes).hexdigest() != header.get("manifest_sha256"):
                    raise SystemExit("empreinte manifest invalide")
                manifest_payload = json.loads(manifest_bytes)
                if manifest_payload.get("kind") != "coderoute_postgres_backup_v1":
                    raise SystemExit("manifest déchiffré invalide")

                manifest_out = output_dir / "coderoute-restored.manifest.json"
                dump_out = output_dir / "coderoute-restored.dump"
                manifest_out.write_bytes(manifest_bytes)
                with dump_out.open("wb") as target:
                    shutil.copyfileobj(clear, target, length=CHUNK)
                os.chmod(manifest_out, 0o600)
                os.chmod(dump_out, 0o600)

            if _sha256(dump_out) != header.get("dump_sha256"):
                dump_out.unlink(missing_ok=True)
                manifest_out.unlink(missing_ok=True)
                raise SystemExit("empreinte dump déchiffré invalide")
            if dump_out.stat().st_size != int(header.get("dump_size_bytes", -1)):
                dump_out.unlink(missing_ok=True)
                manifest_out.unlink(missing_ok=True)
                raise SystemExit("taille dump déchiffré invalide")
            if manifest_payload.get("sha256") != header.get("dump_sha256"):
                raise SystemExit("manifest et header ne désignent pas le même dump")

            return {
                "kind": "coderoute_secure_backup_unpacked_v2",
                "key_id": header.get("key_id"),
                "bundle_sha256": _sha256(bundle),
                "dump_sha256": header.get("dump_sha256"),
                "dump_path": str(dump_out),
                "manifest_path": str(manifest_out),
            }
        finally:
            temp_payload.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    pack_parser = sub.add_parser("pack")
    pack_parser.add_argument("dump")
    pack_parser.add_argument("manifest")
    pack_parser.add_argument("output")
    unpack_parser = sub.add_parser("unpack")
    unpack_parser.add_argument("bundle")
    unpack_parser.add_argument("output_dir")
    args = parser.parse_args()

    if args.command == "pack":
        result = pack(Path(args.dump), Path(args.manifest), Path(args.output))
    else:
        result = unpack(Path(args.bundle), Path(args.output_dir))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

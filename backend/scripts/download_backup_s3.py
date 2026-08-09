#!/usr/bin/env python3
"""Télécharge un bundle de backup chiffré depuis un stockage S3-compatible.

Le téléchargement est vérifié avec le SHA-256 stocké dans les métadonnées de
l'objet avant publication atomique du fichier local.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import boto3

CHUNK = 1024 * 1024


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_endpoint(endpoint: str) -> None:
    if not endpoint:
        return
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" and not _bool("BACKUP_ALLOW_INSECURE_ENDPOINT", False):
        raise SystemExit("BACKUP_S3_ENDPOINT_URL doit utiliser HTTPS")
    if parsed.username or parsed.password:
        raise SystemExit("BACKUP_S3_ENDPOINT_URL ne doit contenir aucun credential")


def download(object_key: str, output: Path) -> dict:
    bucket = os.getenv("BACKUP_S3_BUCKET", "").strip()
    region = os.getenv("BACKUP_TARGET_REGION", "").strip()
    endpoint = os.getenv("BACKUP_S3_ENDPOINT_URL", "").strip()
    if not bucket or not region:
        raise SystemExit("BACKUP_S3_BUCKET et BACKUP_TARGET_REGION sont obligatoires")
    if not object_key or object_key.startswith("/") or ".." in Path(object_key).parts:
        raise SystemExit("object_key invalide")
    _validate_endpoint(endpoint)

    client = boto3.client("s3", region_name=region, endpoint_url=endpoint or None)
    head = client.head_object(Bucket=bucket, Key=object_key)
    metadata = head.get("Metadata") or {}
    expected_sha = str(metadata.get("sha256") or "").lower()
    if len(expected_sha) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha):
        raise SystemExit("métadonnée SHA-256 absente ou invalide")
    if metadata.get("kind") != "coderoute-secure-backup-v2":
        raise SystemExit("type d'objet backup invalide")

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        client.download_file(bucket, object_key, str(temp))
        actual_size = temp.stat().st_size
        expected_size = int(head.get("ContentLength", -1))
        if actual_size != expected_size:
            raise SystemExit("taille backup téléchargé invalide")
        actual_sha = _sha256(temp)
        if actual_sha != expected_sha:
            raise SystemExit("SHA-256 backup téléchargé invalide")
        os.chmod(temp, 0o600)
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)

    result = {
        "kind": "coderoute_offsite_backup_download_v2",
        "bucket": bucket,
        "object_key": object_key,
        "target_region": region,
        "bundle_sha256": expected_sha,
        "bundle_size_bytes": int(head.get("ContentLength", 0)),
        "output": output.name,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("object_key")
    parser.add_argument("output")
    args = parser.parse_args()
    import json
    print(json.dumps(download(args.object_key, Path(args.output)), sort_keys=True))


if __name__ == "__main__":
    main()

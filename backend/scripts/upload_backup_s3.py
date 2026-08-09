#!/usr/bin/env python3
"""Upload d'un bundle CRGBAK2 vers un stockage objet S3-compatible.

Le script refuse une cible dans la même région lorsque BACKUP_REQUIRE_OFF_REGION
est actif. Il ne journalise jamais les credentials ni l'endpoint signé.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import boto3

CHUNK = 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _validate_endpoint(endpoint: str) -> None:
    if not endpoint:
        return
    parsed = urlparse(endpoint)
    allow_insecure = _bool("BACKUP_ALLOW_INSECURE_ENDPOINT", False)
    if parsed.scheme != "https" and not allow_insecure:
        raise SystemExit("BACKUP_S3_ENDPOINT_URL doit utiliser HTTPS")
    if parsed.username or parsed.password:
        raise SystemExit("BACKUP_S3_ENDPOINT_URL ne doit contenir aucun credential")


def upload(bundle: Path, receipt_path: Path) -> dict:
    if not bundle.is_file():
        raise SystemExit("bundle chiffré introuvable")

    bucket = os.getenv("BACKUP_S3_BUCKET", "").strip()
    target_region = os.getenv("BACKUP_TARGET_REGION", "").strip()
    primary_region = os.getenv("BACKUP_PRIMARY_REGION", "").strip()
    require_off_region = _bool("BACKUP_REQUIRE_OFF_REGION", True)
    endpoint = os.getenv("BACKUP_S3_ENDPOINT_URL", "").strip()
    prefix = os.getenv("BACKUP_S3_PREFIX", "coderoute/production").strip("/")
    key_id = os.getenv("BACKUP_ENCRYPTION_KEY_ID", "").strip() or "unversioned"

    if not bucket or not target_region:
        raise SystemExit("BACKUP_S3_BUCKET et BACKUP_TARGET_REGION sont obligatoires")
    if require_off_region:
        if not primary_region:
            raise SystemExit("BACKUP_PRIMARY_REGION est obligatoire pour la règle hors région")
        if primary_region.lower() == target_region.lower():
            raise SystemExit("refus backup: région cible identique à la région primaire")
    _validate_endpoint(endpoint)

    now = datetime.now(UTC)
    object_key = "/".join(
        part for part in (
            prefix,
            now.strftime("%Y"),
            now.strftime("%m"),
            bundle.name,
        ) if part
    )
    sha256 = _sha256(bundle)
    size = bundle.stat().st_size

    client = boto3.client(
        "s3",
        region_name=target_region,
        endpoint_url=endpoint or None,
    )
    extra_args: dict = {
        "ContentType": "application/octet-stream",
        "Metadata": {
            "kind": "coderoute-secure-backup-v2",
            "sha256": sha256,
            "key-id": key_id,
        },
    }
    sse_mode = os.getenv("BACKUP_S3_SSE_MODE", "").strip()
    if sse_mode:
        if sse_mode not in {"AES256", "aws:kms"}:
            raise SystemExit("BACKUP_S3_SSE_MODE doit être AES256 ou aws:kms")
        extra_args["ServerSideEncryption"] = sse_mode
        kms_key = os.getenv("BACKUP_S3_KMS_KEY_ID", "").strip()
        if sse_mode == "aws:kms" and kms_key:
            extra_args["SSEKMSKeyId"] = kms_key

    client.upload_file(str(bundle), bucket, object_key, ExtraArgs=extra_args)
    head = client.head_object(Bucket=bucket, Key=object_key)
    remote_size = int(head.get("ContentLength", -1))
    metadata = head.get("Metadata") or {}
    if remote_size != size or metadata.get("sha256") != sha256:
        raise SystemExit("vérification post-upload échouée")

    receipt = {
        "kind": "coderoute_offsite_backup_receipt_v2",
        "uploaded_at": now.isoformat(),
        "bucket": bucket,
        "object_key": object_key,
        "target_region": target_region,
        "primary_region": primary_region or None,
        "off_region_verified": bool(primary_region and primary_region.lower() != target_region.lower()),
        "bundle_sha256": sha256,
        "bundle_size_bytes": size,
        "encryption_key_id": key_id,
        "server_side_encryption": head.get("ServerSideEncryption") or None,
        "etag": str(head.get("ETag") or "").strip('"') or None,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    os.chmod(receipt_path, 0o600)
    print(json.dumps(receipt, sort_keys=True))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle")
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    upload(Path(args.bundle), Path(args.receipt))


if __name__ == "__main__":
    main()

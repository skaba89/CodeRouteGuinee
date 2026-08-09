import hashlib
import json
from pathlib import Path

import pytest

from scripts import download_backup_s3, upload_backup_s3


class FakeS3:
    def __init__(self):
        self.objects: dict[tuple[str, str], dict] = {}

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        data = Path(filename).read_bytes()
        extra = ExtraArgs or {}
        self.objects[(bucket, key)] = {
            "data": data,
            "metadata": dict(extra.get("Metadata") or {}),
            "sse": extra.get("ServerSideEncryption"),
        }

    def head_object(self, Bucket, Key):
        obj = self.objects[(Bucket, Key)]
        return {
            "ContentLength": len(obj["data"]),
            "Metadata": obj["metadata"],
            "ServerSideEncryption": obj["sse"],
            "ETag": '"fake-etag"',
        }

    def download_file(self, bucket, key, filename):
        Path(filename).write_bytes(self.objects[(bucket, key)]["data"])


def _configure(monkeypatch) -> None:
    monkeypatch.setenv("BACKUP_S3_BUCKET", "coderoute-backups")
    monkeypatch.setenv("BACKUP_PRIMARY_REGION", "frankfurt")
    monkeypatch.setenv("BACKUP_TARGET_REGION", "paris")
    monkeypatch.setenv("BACKUP_REQUIRE_OFF_REGION", "true")
    monkeypatch.setenv("BACKUP_S3_PREFIX", "coderoute/prod")
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY_ID", "backup-key-test")
    monkeypatch.delenv("BACKUP_S3_ENDPOINT_URL", raising=False)


def test_same_region_is_rejected_before_s3_client(monkeypatch, tmp_path: Path) -> None:
    _configure(monkeypatch)
    monkeypatch.setenv("BACKUP_TARGET_REGION", "FRANKFURT")
    called = False

    def forbidden_client(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("S3 client should not be created")

    monkeypatch.setattr(upload_backup_s3.boto3, "client", forbidden_client)
    bundle = tmp_path / "backup.crgbak"
    bundle.write_bytes(b"ciphertext")
    with pytest.raises(SystemExit, match="région cible"):
        upload_backup_s3.upload(bundle, tmp_path / "receipt.json")
    assert called is False


def test_insecure_endpoint_is_rejected(monkeypatch, tmp_path: Path) -> None:
    _configure(monkeypatch)
    monkeypatch.setenv("BACKUP_S3_ENDPOINT_URL", "http://objects.example.test")
    bundle = tmp_path / "backup.crgbak"
    bundle.write_bytes(b"ciphertext")
    with pytest.raises(SystemExit, match="HTTPS"):
        upload_backup_s3.upload(bundle, tmp_path / "receipt.json")


def test_upload_and_download_verify_sha_without_exposing_credentials(monkeypatch, tmp_path: Path) -> None:
    _configure(monkeypatch)
    fake = FakeS3()
    monkeypatch.setattr(upload_backup_s3.boto3, "client", lambda *a, **k: fake)
    monkeypatch.setattr(download_backup_s3.boto3, "client", lambda *a, **k: fake)

    bundle = tmp_path / "coderoute.crgbak"
    bundle.write_bytes(b"encrypted-backup" * 100)
    receipt_path = tmp_path / "receipt.json"
    receipt = upload_backup_s3.upload(bundle, receipt_path)

    assert receipt["off_region_verified"] is True
    assert receipt["bundle_sha256"] == hashlib.sha256(bundle.read_bytes()).hexdigest()
    rendered = receipt_path.read_text(encoding="utf-8")
    assert "AWS_SECRET_ACCESS_KEY" not in rendered
    assert "endpoint" not in rendered.lower()

    restored = tmp_path / "retrieved.crgbak"
    result = download_backup_s3.download(receipt["object_key"], restored)
    assert restored.read_bytes() == bundle.read_bytes()
    assert result["bundle_sha256"] == receipt["bundle_sha256"]


def test_download_rejects_missing_sha_metadata(monkeypatch, tmp_path: Path) -> None:
    _configure(monkeypatch)
    fake = FakeS3()
    fake.objects[("coderoute-backups", "bad.crgbak")] = {
        "data": b"bad",
        "metadata": {"kind": "coderoute-secure-backup-v2"},
        "sse": None,
    }
    monkeypatch.setattr(download_backup_s3.boto3, "client", lambda *a, **k: fake)
    with pytest.raises(SystemExit, match="SHA-256"):
        download_backup_s3.download("bad.crgbak", tmp_path / "out.crgbak")

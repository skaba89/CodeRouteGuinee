from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_media_deployment.py"
spec = importlib.util.spec_from_file_location("verify_media_deployment", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _webp() -> bytes:
    return b"RIFF" + (20).to_bytes(4, "little") + b"WEBP" + b"VP8 " + b"x" * 32


def _mp4() -> bytes:
    return b"\x00\x00\x00\x18ftypisom" + b"x" * 64


def _manifest() -> dict:
    return {
        "schema_version": 1,
        "governance": {
            "source_type": "generated",
            "quality_status": "DEMO_NOT_OFFICIAL",
            "regulatory_status": "NOT_REVIEWED",
            "official_exam_allowed": False,
        },
        "assets": [
            {"file": "a.webp", "kind": "image", "question_keys": ["stop"]},
            {"file": "b.webp", "kind": "image", "question_keys": ["give_way"]},
            {"file": "c.webp", "kind": "image", "question_keys": ["no_entry"]},
            {
                "file": "d.mp4",
                "kind": "video",
                "duration_seconds": 6,
                "question_keys": ["roundabout"],
                "poster": "b.webp",
                "fallback": "b.webp",
            },
        ],
    }


def test_media_deployment_receipt_passes_for_expected_public_pack(monkeypatch):
    manifest_raw = json.dumps(_manifest()).encode("utf-8")

    def fake_request(_base_url, path, _timeout, *, max_bytes):
        assert max_bytes > 0
        if path.endswith("manifest.json"):
            return 200, manifest_raw, "application/json; charset=utf-8", None
        if path.endswith(".webp"):
            return 200, _webp(), "image/webp", None
        if path.endswith(".mp4"):
            return 200, _mp4(), "video/mp4", None
        raise AssertionError(path)

    monkeypatch.setattr(module, "request_bytes", fake_request)
    receipt = module.build_receipt(
        frontend_url="https://coderouteguinee-frontend.onrender.com",
        manifest_path="/media/exam/guinea/manifest.json",
        timeout=5,
    )
    assert receipt["passed"] is True
    assert receipt["blockers"] == []
    assert len(receipt["assets"]) == 4
    assert receipt["institutional_validation_inferred"] is False


def test_media_deployment_receipt_fails_closed_if_manifest_claims_official(monkeypatch):
    manifest = _manifest()
    manifest["governance"]["official_exam_allowed"] = True
    raw = json.dumps(manifest).encode("utf-8")

    def fake_request(_base_url, path, _timeout, *, max_bytes):
        if path.endswith("manifest.json"):
            return 200, raw, "application/json", None
        if path.endswith(".webp"):
            return 200, _webp(), "image/webp", None
        return 200, _mp4(), "video/mp4", None

    monkeypatch.setattr(module, "request_bytes", fake_request)
    receipt = module.build_receipt(
        frontend_url="https://coderouteguinee-frontend.onrender.com",
        manifest_path="/media/exam/guinea/manifest.json",
        timeout=5,
    )
    assert receipt["passed"] is False
    assert "OFFICIAL_EXAM_FORBIDDEN" in receipt["blockers"]


def test_media_deployment_rejects_non_webp_payload_even_with_image_content_type():
    result = module.evaluate_asset(
        {"file": "broken.webp", "kind": "image"},
        status_code=200,
        raw=b"<html>SPA fallback</html>",
        content_type="image/webp",
        error=None,
    )
    assert result["passed"] is False
    assert "MAGIC_BYTES" in result["blockers"]


def test_media_deployment_frontend_url_policy_requires_https_outside_localhost():
    assert module.safe_base_url("https://example.onrender.com") == "https://example.onrender.com"
    try:
        module.safe_base_url("http://example.onrender.com")
    except ValueError as exc:
        assert "HTTP non chiffré" in str(exc)
    else:
        raise AssertionError("plain HTTP should be rejected")

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_media_library.py"
spec = importlib.util.spec_from_file_location("audit_media_library", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _question(*, text: str, media_type: str | None, media_url: str | None, media_alt: str | None = "Visuel"):
    return SimpleNamespace(text=text, media_type=media_type, media_url=media_url, media_alt=media_alt)


def test_missing_media_is_classified_missing():
    status, reasons = module.classify(_question(text="Question", media_type=None, media_url=None))
    assert status == "MISSING"
    assert reasons


def test_legacy_scene_is_never_considered_premium_validated():
    status, reasons = module.classify(
        _question(text="Quelle distance de sécurité ?", media_type="scene", media_url="situation_safe_distance")
    )
    assert status == "REVIEW_REQUIRED"
    assert any("legacy" in reason.lower() for reason in reasons)


def test_high_confidence_semantic_mismatch_is_rejected():
    status, reasons = module.classify(
        _question(text="Sur une chaussée verglacée, que faites-vous ?", media_type="scene", media_url="situation_emergency_vehicle")
    )
    assert status == "REJECTED"
    assert any("verglas" in reason.lower() for reason in reasons)


def test_real_remote_media_without_provenance_is_not_declared_validated(monkeypatch):
    monkeypatch.setattr(module, "validate_media_url", lambda value, _kind: value)
    status, reasons = module.classify(
        _question(
            text="Situation réelle",
            media_type="image",
            media_url="https://cdn.coderoute.example/question.webp",
        )
    )
    assert status == "COPYRIGHT_UNKNOWN"
    assert any("licence" in reason.lower() for reason in reasons)


def test_unknown_media_type_is_rejected():
    status, _ = module.classify(
        _question(text="Question", media_type="pdf", media_url="https://cdn.coderoute.example/file.pdf")
    )
    assert status == "REJECTED"

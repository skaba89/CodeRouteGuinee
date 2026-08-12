from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "frontend" / "src" / "components" / "ExamMediaRuntime.tsx"
PUBLIC_API = ROOT / "frontend" / "src" / "pages" / "shared-exam-components.tsx"


def test_exam_runtime_prefers_explicit_fallback_and_keeps_cloudinary_compatibility():
    source = RUNTIME.read_text(encoding="utf-8")
    assert "res.cloudinary.com" in source
    assert "/video/upload/" in source
    assert "const effectivePoster = poster || derivedPoster" in source
    assert "const effectiveFallback = fallback || effectivePoster" in source
    assert "fallbackUrl={effectiveFallback}" in source
    assert "poster={effectivePoster}" in source
    assert "PremiumMediaBlock" in source


def test_exam_public_component_api_points_to_resilient_runtime_facade():
    source = PUBLIC_API.read_text(encoding="utf-8")
    assert "../components/ExamMediaRuntime" in source
    assert "shared-exam-components-legacy" in source
    assert "MediaBlock, VideoPlayer" in source

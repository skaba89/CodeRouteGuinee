from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "frontend" / "src" / "components" / "ExamMediaRuntime.tsx"
PUBLIC_API = ROOT / "frontend" / "src" / "pages" / "shared-exam-components.tsx"


def test_exam_runtime_uses_cloudinary_poster_as_mobile_video_fallback():
    source = RUNTIME.read_text(encoding="utf-8")
    assert "res.cloudinary.com" in source
    assert "/video/upload/" in source
    assert "fallbackUrl={poster}" in source
    assert "poster={poster}" in source
    assert "PremiumMediaBlock" in source


def test_exam_public_component_api_points_to_resilient_runtime_facade():
    source = PUBLIC_API.read_text(encoding="utf-8")
    assert "../components/ExamMediaRuntime" in source
    assert "shared-exam-components-legacy" in source
    assert "MediaBlock, VideoPlayer" in source

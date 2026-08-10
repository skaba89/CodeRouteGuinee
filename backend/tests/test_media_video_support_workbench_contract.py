from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKBENCH = ROOT / "frontend" / "src" / "components" / "MediaVideoSupportWorkbench.tsx"
CLIENT = ROOT / "frontend" / "src" / "mediaVideoApi.ts"
COMPOSED = ROOT / "frontend" / "src" / "pages" / "media-library-v2.tsx"


def test_video_support_workbench_requires_validated_images_and_explicit_poster_fallback():
    source = WORKBENCH.read_text(encoding="utf-8")
    assert "media_type: 'video'" in source
    assert "usage_type: 'exam'" in source
    assert "media_type: 'image'" in source
    assert "quality_status: 'validated'" in source
    assert "poster_media_id" in source
    assert "fallback_media_id" in source
    assert "Enregistrer poster + fallback" in source
    assert "Le poster/fallback n’accorde jamais une homologation DNTT automatiquement" in source


def test_video_support_client_updates_media_asset_with_csrf_protected_patch():
    source = CLIENT.read_text(encoding="utf-8")
    assert "method: 'PATCH'" in source
    assert "X-CSRF-Token" in source
    assert "poster_media_id: posterMediaId" in source
    assert "fallback_media_id: fallbackMediaId" in source
    assert "/api/v1/media-library/assets/" in source


def test_composed_media_library_includes_video_support_workbench_additively():
    source = COMPOSED.read_text(encoding="utf-8")
    assert "MediaLibraryCore" in source
    assert "MediaQuestionMappingWorkbench" in source
    assert "MediaVideoSupportWorkbench" in source
    assert "<MediaVideoSupportWorkbench />" in source

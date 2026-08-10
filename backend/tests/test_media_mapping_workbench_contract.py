from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKBENCH = ROOT / "frontend" / "src" / "components" / "MediaQuestionMappingWorkbench.tsx"
CLIENT = ROOT / "frontend" / "src" / "mediaQuestionApi.ts"
COMPOSED_PAGE = ROOT / "frontend" / "src" / "pages" / "media-library-v2.tsx"
PAGES_INDEX = ROOT / "frontend" / "src" / "pages" / "index.ts"


def test_media_mapping_workbench_is_manual_audited_and_primary_fail_closed():
    source = WORKBENCH.read_text(encoding="utf-8")

    assert "Aucun mapping automatique" in source
    assert "linkQuestionMedia" in source
    assert "unlinkQuestionMedia" in source
    assert "quality_status: 'validated'" in source
    assert "regulatory_status: role === 'primary' ? 'validated' : undefined" in source
    assert "selectedAsset.quality_status !== 'validated'" in source
    assert "selectedAsset.regulatory_status !== 'validated'" in source
    assert "selectedAsset.usage_type !== 'exam'" in source
    assert '<option value="primary">' in source
    assert '<option value="explanation">' in source
    # Do not pretend question-level poster/fallback links configure an official video asset.
    assert '<option value="poster">' not in source
    assert '<option value="fallback">' not in source
    assert "poster_media_id" in source and "fallback_media_id" in source


def test_media_mapping_client_uses_existing_audited_backend_endpoints_and_csrf_delete():
    source = CLIENT.read_text(encoding="utf-8")
    assert "/api/v1/media-library/questions/" in source
    assert "/links" in source
    assert "method: 'DELETE'" in source
    assert "X-CSRF-Token" in source
    assert "fetchWithAuth" in source


def test_media_library_composition_is_additive_and_preserves_existing_core_page():
    composed = COMPOSED_PAGE.read_text(encoding="utf-8")
    index = PAGES_INDEX.read_text(encoding="utf-8")

    assert "MediaLibraryPage as MediaLibraryCore" in composed
    assert "<MediaLibraryCore />" in composed
    assert "<MediaQuestionMappingWorkbench />" in composed
    assert "export { MediaLibraryPage } from './media-library-v2';" in index

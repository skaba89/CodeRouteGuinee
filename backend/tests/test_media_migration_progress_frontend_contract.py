from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "frontend" / "src" / "mediaProgressApi.ts"
PANEL = ROOT / "frontend" / "src" / "components" / "MediaMigrationProgressPanel.tsx"
COMPOSED = ROOT / "frontend" / "src" / "pages" / "media-library-v2.tsx"


def test_media_progress_client_targets_admin_only_migration_endpoint():
    source = CLIENT.read_text(encoding="utf-8")
    assert "/api/v1/media-library/migration-progress" in source
    assert "publishable_premium" in source
    assert "legacy_only" in source
    assert "institutional_validation_inferred" in source


def test_media_progress_panel_is_operator_triggered_and_does_not_auto_fetch():
    source = PANEL.read_text(encoding="utf-8")
    assert "Actualiser la progression" in source
    assert "onClick={() => void refresh()}" in source
    assert "useEffect" not in source
    assert "publishable_percent" in source
    assert "normalized_blocked" in source
    assert "legacy_only" in source
    assert "ne déclare aucune homologation institutionnelle" in source


def test_media_library_composes_progress_before_mapping_and_video_tools():
    source = COMPOSED.read_text(encoding="utf-8")
    progress = source.index("<MediaMigrationProgressPanel />")
    mapping = source.index("<MediaQuestionMappingWorkbench focusQuestion={focusedQuestion} />")
    video = source.index("<MediaVideoSupportWorkbench />")
    assert progress < mapping < video

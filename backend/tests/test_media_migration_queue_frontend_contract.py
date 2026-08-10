from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "frontend" / "src" / "mediaQueueApi.ts"
PANEL = ROOT / "frontend" / "src" / "components" / "MediaMigrationQueuePanel.tsx"
MAPPING = ROOT / "frontend" / "src" / "components" / "MediaQuestionMappingWorkbench.tsx"
COMPOSED = ROOT / "frontend" / "src" / "pages" / "media-library-v2.tsx"


def test_media_queue_client_targets_admin_only_action_queue():
    source = CLIENT.read_text(encoding="utf-8")
    assert "/api/v1/media-library/migration-queue" in source
    assert "normalized_blocked" in source
    assert "legacy_only" in source
    assert "no_media" in source
    assert "blocker_codes" in source
    assert "institutional_validation_inferred" in source


def test_media_queue_panel_is_operator_triggered_and_never_auto_maps():
    source = PANEL.read_text(encoding="utf-8")
    assert "Actualiser la file" in source
    assert "Traiter cette question" in source
    assert "Aucun média n’est choisi automatiquement" in source
    assert "onMapQuestion" in source
    assert "blocker_codes" in source
    assert "REGULATORY_APPROVED" not in source  # blockers are data-driven, not hard-coded guesses
    assert "useEffect" not in source


def test_mapping_workbench_accepts_explicit_focus_from_queue():
    source = MAPPING.read_text(encoding="utf-8")
    assert "focusQuestion" in source
    assert "mapping-focused-question" in source
    assert "listQuestionMedia(question.id)" in source
    assert "Aucun mapping automatique" in source


def test_media_library_places_action_queue_before_mapping_workbench():
    source = COMPOSED.read_text(encoding="utf-8")
    progress = source.index("<MediaMigrationProgressPanel />")
    queue = source.index("<MediaMigrationQueuePanel")
    mapping = source.index("<MediaQuestionMappingWorkbench")
    video = source.index("<MediaVideoSupportWorkbench />")
    assert progress < queue < mapping < video
    assert "setFocusedQuestion" in source

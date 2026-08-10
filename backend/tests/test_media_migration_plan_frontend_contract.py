from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "frontend" / "src" / "mediaMigrationPlanApi.ts"
PANEL = ROOT / "frontend" / "src" / "components" / "MediaBatchMigrationWorkbench.tsx"
COMPOSED = ROOT / "frontend" / "src" / "pages" / "media-library-v2.tsx"


def test_batch_migration_client_uses_single_admin_endpoint():
    source = CLIENT.read_text(encoding="utf-8")
    assert "/api/v1/media-library/migration-plan" in source
    assert "dry_run" in source
    assert "replace_existing" in source
    assert "institutional_validation_inferred" in source


def test_batch_migration_ui_requires_dry_run_before_apply():
    source = PANEL.read_text(encoding="utf-8")
    assert "Dry-run complet" in source
    assert "Appliquer le lot" in source
    assert "validatedFingerprint" in source
    assert "validatedFingerprint === currentFingerprint" in source
    assert "runMediaMigrationPlan" in source
    assert "dry_run: true" in source
    assert "dry_run: false" in source
    assert "Aucun" not in source or "mapping" in source
    assert "ne constitue jamais une homologation DNTT" in source


def test_batch_migration_ui_keeps_primary_replacement_super_admin_only():
    source = PANEL.read_text(encoding="utf-8")
    assert "isSuperAdmin" in source
    assert "replaceExisting" in source
    assert "remplacement d’un primary existant exige un super_admin" in source


def test_media_library_places_batch_plan_after_queue_before_manual_mapping():
    source = COMPOSED.read_text(encoding="utf-8")
    queue = source.index("<MediaMigrationQueuePanel")
    batch = source.index("<MediaBatchMigrationWorkbench />")
    mapping = source.index("<MediaQuestionMappingWorkbench")
    assert queue < batch < mapping

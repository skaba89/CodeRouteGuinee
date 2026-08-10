from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "frontend" / "src" / "components" / "MediaMigrationQueuePanel.tsx"
BATCH = ROOT / "frontend" / "src" / "components" / "MediaBatchMigrationWorkbench.tsx"
E2E = ROOT / "frontend" / "tests" / "e2e" / "media-migration-workflow.spec.ts"


def test_queue_exports_batch_compatible_csv_for_full_question_bank():
    source = QUEUE.read_text(encoding="utf-8")
    assert "limit: 200" in source
    assert "question_id" in source and "media_id" in source
    assert "buildBatchTemplate" in source
    assert "export-media-queue-csv" in source
    assert "coderoute-media-migration-${stateFilter}.csv" in source
    assert "Aucun média n’est choisi automatiquement" in source


def test_batch_import_accepts_exported_context_columns_and_invalidates_dry_run():
    source = BATCH.read_text(encoding="utf-8")
    assert "import-media-migration-csv" in source
    assert "replace(/^\\uFEFF/" in source
    assert "cleanCsvCell" in source
    assert "parts[0]" in source and "parts[1]" in source
    assert "Les colonnes après `media_id` sont ignorées" in source
    assert "invalidateDryRun" in source
    assert "setValidatedFingerprint('')" in source


def test_media_migration_e2e_covers_download_and_file_import():
    source = E2E.read_text(encoding="utf-8")
    assert "waitForEvent('download')" in source
    assert "export-media-queue-csv" in source
    assert "import-media-migration-csv" in source
    assert "setInputFiles" in source
    assert "\\uFEFFquestion_id;media_id" in source
    assert "[true, false]" in source

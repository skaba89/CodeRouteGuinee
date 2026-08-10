from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "media-migration-readiness.yml"
E2E = ROOT / "frontend" / "tests" / "e2e" / "media-migration-workflow.spec.ts"


def test_media_migration_readiness_compiles_all_runtime_and_migration_modules():
    source = WORKFLOW.read_text(encoding="utf-8")
    for marker in (
        "app/exam_media_resolver.py",
        "app/routers/exam_media_guard.py",
        "app/routers/media_migration_progress.py",
        "app/routers/media_migration_queue.py",
        "app/routers/media_migration_plan.py",
        "app/routers/media_link_guard.py",
        "app/schemas_media_migration.py",
        "tests/test_media_*.py",
    ):
        assert marker in source, marker


def test_media_migration_readiness_runs_typecheck_build_security_and_e2e():
    source = WORKFLOW.read_text(encoding="utf-8")
    for marker in (
        "npm ci",
        "npm run audit:security",
        "npm run typecheck",
        "npm run build",
        "tests/e2e/media-library.spec.ts",
        "tests/e2e/media-migration-workflow.spec.ts",
        "--project=chromium",
    ):
        assert marker in source, marker


def test_media_migration_e2e_proves_queue_handoff_and_dry_run_before_apply():
    source = E2E.read_text(encoding="utf-8")
    assert "refresh-media-queue" in source
    assert "treat-media-question-q-legacy-001" in source
    assert "mapping-focused-question" in source
    assert "dry-run-media-migration-plan" in source
    assert "apply-media-migration-plan" in source
    assert "toBeDisabled" in source
    assert "toBeEnabled" in source
    assert "[true, false]" in source

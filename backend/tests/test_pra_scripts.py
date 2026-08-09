from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (BACKEND_ROOT / relative).read_text(encoding="utf-8")


def test_predeploy_is_fail_closed_and_does_not_log_database_url():
    script = _text("scripts/predeploy.sh")
    assert "set -euo pipefail" in script
    assert "alembic upgrade head" in script
    assert "|| echo" not in script
    assert 'echo "$MIGRATE_URL"' not in script


def test_production_entrypoint_does_not_migrate_or_seed_by_default():
    script = _text("entrypoint.sh")
    assert "RUN_MIGRATIONS_ON_STARTUP_VALUE=false" in script
    assert "RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE=false" in script
    assert "./scripts/predeploy.sh" in script


def test_restore_drill_refuses_protected_database_and_requires_opt_in():
    script = _text("scripts/restore_drill.sh")
    assert "ALLOW_DESTRUCTIVE_RESTORE_DRILL" in script
    assert "DATABASE_URL" in script
    assert "ALEMBIC_DATABASE_URL" in script
    assert "BACKUP_DATABASE_URL" in script
    assert "refus de restaurer dans une base source/production protégée" in script
    assert "sha256sum" in script


def test_backup_has_checksum_manifest_and_no_plaintext_url_output():
    script = _text("scripts/backup_postgres.sh")
    assert "pg_dump" in script
    assert "sha256sum" in script
    assert "coderoute_postgres_backup_v1" in script
    assert 'echo "$SOURCE_URL"' not in script
    assert 'echo "$PG_URL"' not in script

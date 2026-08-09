import os
import subprocess
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
    assert "db_identity" in script
    assert "refus de restaurer dans une base source/production protégée" in script
    assert "sha256sum" in script


def test_restore_drill_rejects_same_database_with_different_credentials_and_query(tmp_path):
    dump = tmp_path / "unused.dump"
    manifest = tmp_path / "unused.json"
    env = os.environ.copy()
    env.update({
        "ALLOW_DESTRUCTIVE_RESTORE_DRILL": "true",
        "RESTORE_DATABASE_URL": "postgresql://drill:newpass@DB.EXAMPLE:5432/coderoute?sslmode=require",
        "DATABASE_URL": "postgresql+psycopg://prod:secret@db.example/coderoute?application_name=prod",
    })
    result = subprocess.run(
        ["bash", str(BACKEND_ROOT / "scripts/restore_drill.sh"), str(dump), str(manifest)],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "base source/production protégée" in result.stderr
    assert "pg_restore" not in result.stdout


def test_backup_has_checksum_manifest_and_no_plaintext_url_output():
    script = _text("scripts/backup_postgres.sh")
    assert "pg_dump" in script
    assert "sha256sum" in script
    assert "coderoute_postgres_backup_v1" in script
    assert 'echo "$SOURCE_URL"' not in script
    assert 'echo "$PG_URL"' not in script

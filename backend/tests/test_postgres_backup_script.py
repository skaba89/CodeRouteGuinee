import importlib.util
from datetime import datetime, timezone
from pathlib import Path


def load_backup_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "postgres_backup.py"
    spec = importlib.util.spec_from_file_location("postgres_backup", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_database_url_from_env_normalizes_psycopg_scheme() -> None:
    backup = load_backup_module()

    database_url = backup.database_url_from_env(
        {"DATABASE_URL": "postgresql+psycopg://coderoute:secret@postgres:5432/coderoute"}
    )

    assert database_url == "postgresql://coderoute:secret@postgres:5432/coderoute"


def test_timestamped_backup_path_uses_utc_prefix() -> None:
    backup = load_backup_module()
    now = datetime(2026, 6, 18, 16, 30, 5, tzinfo=timezone.utc)

    path = backup.timestamped_backup_path("backups/postgres", "coderoute-guinee", now)

    assert path == Path("backups/postgres/coderoute-guinee-20260618T163005Z.backup")


def test_build_backup_command_uses_custom_format_without_owner() -> None:
    backup = load_backup_module()
    command = backup.build_backup_command("postgresql://u:p@host:5432/db", Path("backup.dump"))

    assert command == [
        "pg_dump",
        "postgresql://u:p@host:5432/db",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        "backup.dump",
    ]


def test_restore_requires_confirmation(tmp_path) -> None:
    backup = load_backup_module()
    env_file = tmp_path / ".env"
    env_file.write_text('DATABASE_URL="postgresql://u:p@host:5432/db"', encoding="utf-8")

    result = backup.main(["--env-file", str(env_file), "--dry-run", "restore", "missing.backup"])

    assert result == 2


def test_restore_dry_run_accepts_confirmation(tmp_path) -> None:
    backup = load_backup_module()
    env_file = tmp_path / ".env"
    env_file.write_text('DATABASE_URL="postgresql://u:p@host:5432/db"', encoding="utf-8")

    result = backup.main(["--env-file", str(env_file), "--dry-run", "restore", "missing.backup", "--confirm-restore", "--clean"])

    assert result == 0

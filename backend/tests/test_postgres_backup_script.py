import importlib.util
from datetime import UTC, datetime
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
    now = datetime(2026, 6, 18, 16, 30, 5, tzinfo=UTC)

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


def test_restore_command_uses_clean_if_exists() -> None:
    """La restauration doit utiliser --clean --if-exists pour être fiable
    sur une base partiellement peuplée (cas réel post-incident)."""
    backup = load_backup_module()
    cmd = backup.build_restore_command("postgresql://u:p@host/db", Path("b.backup"), clean=True)
    assert "--clean" in cmd
    assert "--if-exists" in cmd
    # Sans --exit-on-error : ne doit pas s'arrêter à la première table existante
    assert "--exit-on-error" not in cmd


def test_verify_backup_file_rejects_missing() -> None:
    backup = load_backup_module()
    assert backup.verify_backup_file(Path("/tmp/inexistant-xyz.backup")) is False


def test_verify_backup_file_rejects_empty(tmp_path) -> None:
    backup = load_backup_module()
    empty = tmp_path / "vide.backup"
    empty.write_bytes(b"")
    assert backup.verify_backup_file(empty) is False


def test_latest_backup_returns_none_when_empty(tmp_path) -> None:
    backup = load_backup_module()
    assert backup.latest_backup(tmp_path, "coderoute-guinee") is None


def test_latest_backup_returns_most_recent(tmp_path) -> None:
    backup = load_backup_module()
    (tmp_path / "coderoute-guinee-20260101T000000Z.backup").write_bytes(b"x")
    (tmp_path / "coderoute-guinee-20260601T000000Z.backup").write_bytes(b"x")
    latest = backup.latest_backup(tmp_path, "coderoute-guinee")
    assert latest is not None and "20260601" in latest.name


def test_retention_keeps_at_least_one(tmp_path) -> None:
    """La rétention ne supprime jamais le dernier backup, même très ancien."""
    backup = load_backup_module()
    only = tmp_path / "coderoute-guinee-20200101T000000Z.backup"
    only.write_bytes(b"x")
    deleted = backup.apply_retention(tmp_path, "coderoute-guinee", retention_days=1)
    assert deleted == []
    assert only.exists()


def test_retention_removes_old_keeps_recent(tmp_path) -> None:
    import os
    import time
    backup = load_backup_module()
    old = tmp_path / "coderoute-guinee-20200101T000000Z.backup"
    recent = tmp_path / "coderoute-guinee-20260601T000000Z.backup"
    old.write_bytes(b"x")
    recent.write_bytes(b"x")
    # Vieillir artificiellement le fichier 'old'
    old_time = time.time() - 40 * 86400  # 40 jours
    os.utime(old, (old_time, old_time))
    deleted = backup.apply_retention(tmp_path, "coderoute-guinee", retention_days=7)
    assert old in deleted
    assert recent.exists()

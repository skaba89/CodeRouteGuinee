import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_BACKUP_DIR = "backups/postgres"
DEFAULT_PREFIX = "coderoute-guinee"


def parse_env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().lstrip("\ufeff")] = value.strip().strip('"').strip("'")
    return values


def database_url_from_env(values: dict[str, str]) -> str:
    database_url = values.get("DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    return database_url.replace("postgresql+psycopg://", "postgresql://")


def timestamped_backup_path(backup_dir: str, prefix: str, now: datetime | None = None) -> Path:
    current_time = now or datetime.now(timezone.utc)
    timestamp = current_time.strftime("%Y%m%dT%H%M%SZ")
    return Path(backup_dir) / f"{prefix}-{timestamp}.backup"


def build_backup_command(database_url: str, output_path: Path) -> list[str]:
    return [
        "pg_dump",
        database_url,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(output_path),
    ]


def build_restore_command(database_url: str, backup_path: Path, clean: bool) -> list[str]:
    command = ["pg_restore", "--dbname", database_url]
    if clean:
        command.extend(["--clean", "--if-exists"])
    command.append(str(backup_path))
    return command


def run_command(command: list[str], dry_run: bool) -> int:
    print(" ".join(command))
    if dry_run:
        return 0
    completed = subprocess.run(command, check=False)
    return completed.returncode


def backup(args: argparse.Namespace) -> int:
    values = parse_env_file(args.env_file)
    database_url = database_url_from_env(values)
    output_path = Path(args.output) if args.output else timestamped_backup_path(args.backup_dir, args.prefix)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return run_command(build_backup_command(database_url, output_path), args.dry_run)


def restore(args: argparse.Namespace) -> int:
    if not args.confirm_restore:
        print("ERROR - restore requires --confirm-restore", file=sys.stderr)
        return 2
    values = parse_env_file(args.env_file)
    database_url = database_url_from_env(values)
    backup_path = Path(args.backup_file)
    if not backup_path.exists() and not args.dry_run:
        print(f"ERROR - backup file not found: {backup_path}", file=sys.stderr)
        return 1
    return run_command(build_restore_command(database_url, backup_path, args.clean), args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CodeRoute Guinee PostgreSQL backup and restore")
    parser.add_argument("--env-file", default=".env", help="Env file containing DATABASE_URL")
    parser.add_argument("--dry-run", action="store_true", help="Print the command without executing it")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create a PostgreSQL custom-format backup")
    backup_parser.add_argument("--backup-dir", default=DEFAULT_BACKUP_DIR)
    backup_parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    backup_parser.add_argument("--output", default="")
    backup_parser.set_defaults(handler=backup)

    restore_parser = subparsers.add_parser("restore", help="Restore a PostgreSQL custom-format backup")
    restore_parser.add_argument("backup_file")
    restore_parser.add_argument("--clean", action="store_true", help="Drop objects before restoring")
    restore_parser.add_argument("--confirm-restore", action="store_true", help="Required safety switch for restore")
    restore_parser.set_defaults(handler=restore)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except ValueError as exc:
        print(f"ERROR - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

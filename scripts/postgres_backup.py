#!/usr/bin/env python3
"""
Script de sauvegarde PostgreSQL — CodeRoute Guinée

API publique (utilisée par les tests) :
  database_url_from_env(env: dict) -> str
  timestamped_backup_path(backup_dir, prefix, now) -> Path
  build_backup_command(db_url, dest_path) -> list[str]
  main(argv=None) -> int

Usage CLI :
  python scripts/postgres_backup.py backup
  python scripts/postgres_backup.py restore backup.dump --confirm-restore
  python scripts/postgres_backup.py --dry-run restore backup.dump --confirm-restore
  python scripts/postgres_backup.py --env-file .env backup
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


# ── Fonctions utilitaires (API publique) ─────────────────────────────────────

def database_url_from_env(env: dict[str, str] | None = None) -> str:
    """
    Lit DATABASE_URL depuis le dict d'env fourni (ou os.environ).
    Normalise postgresql+psycopg:// → postgresql:// pour pg_dump/pg_restore.
    """
    if env is None:
        env = dict(os.environ)
    url = env.get("DATABASE_URL", "")
    # pg_dump ne comprend pas +psycopg — le supprimer
    return re.sub(r"postgresql\+\w+://", "postgresql://", url)


def timestamped_backup_path(
    backup_dir: str | Path,
    prefix: str,
    now: datetime | None = None,
) -> Path:
    """Construit le chemin de destination avec horodatage UTC."""
    if now is None:
        now = datetime.now(UTC)
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    return Path(backup_dir) / f"{prefix}-{ts}.backup"


def build_backup_command(db_url: str, dest_path: str | Path) -> list[str]:
    """Construit la commande pg_dump pour le format custom (restaurable via pg_restore)."""
    return [
        "pg_dump",
        db_url,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(dest_path),
    ]


def build_restore_command(db_url: str, backup_path: str | Path, clean: bool) -> list[str]:
    """Construit la commande pg_restore."""
    cmd = [
        "pg_restore",
        "--dbname", db_url,
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
    ]
    if clean:
        cmd.append("--clean")
    cmd.append(str(backup_path))
    return cmd


def parse_env_file(path: str) -> dict[str, str]:
    """Lit un fichier .env et retourne un dict de clé=valeur."""
    env: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL backup/restore — CodeRoute Guinée")
    parser.add_argument("--env-file",  help="Fichier .env à charger")
    parser.add_argument("--dry-run",   action="store_true", help="Simuler sans exécuter")
    parser.add_argument("--backup-dir", default=os.environ.get("BACKUP_DIR", "/var/backups/coderoute"))
    parser.add_argument("--prefix",    default="coderoute-guinee")

    sub = parser.add_subparsers(dest="command")

    # Sous-commande backup
    sub.add_parser("backup", help="Créer un backup")

    # Sous-commande restore
    restore_parser = sub.add_parser("restore", help="Restaurer un backup")
    restore_parser.add_argument("backup_file")
    restore_parser.add_argument("--confirm-restore", action="store_true",
                                help="Confirmer explicitement la restauration")
    restore_parser.add_argument("--clean", action="store_true",
                                help="Supprimer les objets existants avant restauration")

    args = parser.parse_args(argv)

    # Charger l'env
    env = dict(os.environ)
    if args.env_file:
        env.update(parse_env_file(args.env_file))

    db_url = database_url_from_env(env)

    if args.command == "restore":
        # La restauration requiert une confirmation explicite
        if not args.confirm_restore:
            print("❌ La restauration requiert --confirm-restore", file=sys.stderr)
            return 2

        backup_path = Path(args.backup_file)
        cmd = build_restore_command(db_url, backup_path, args.clean)
        print(f"{'[DRY-RUN] ' if args.dry_run else ''}pg_restore : {backup_path}")
        if args.dry_run:
            return 0
        result = subprocess.run(cmd)
        return result.returncode

    else:
        # Backup (défaut)
        dest = timestamped_backup_path(args.backup_dir, args.prefix)
        Path(args.backup_dir).mkdir(parents=True, exist_ok=True)
        cmd = build_backup_command(db_url, dest)
        print(f"{'[DRY-RUN] ' if args.dry_run else ''}pg_dump → {dest}")
        if args.dry_run:
            return 0
        result = subprocess.run(cmd)
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())

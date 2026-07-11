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
    """Construit la commande pg_restore.

    --clean --if-exists : supprime proprement les objets existants avant de
    les recréer, ce qui rend la restauration fiable que la base soit vide,
    partiellement peuplée ou complète. Sans cela, pg_restore échoue dès la
    première table déjà présente (cas réel d'une restauration post-incident).
    """
    cmd = [
        "pg_restore",
        "--dbname", db_url,
        "--no-owner",
        "--no-privileges",
    ]
    if clean:
        cmd.extend(["--clean", "--if-exists"])
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


def verify_backup_file(backup_path: str | Path) -> bool:
    """
    Vérifie qu'un fichier est une archive pg_dump custom valide et lisible.

    Utilise `pg_restore --list` : si l'archive est corrompue ou vide,
    pg_restore échoue → le backup n'est pas fiable.
    """
    path = Path(backup_path)
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        result = subprocess.run(
            ["pg_restore", "--list", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        # Une archive valide liste au moins une entrée (TABLE, SEQUENCE, etc.)
        return result.returncode == 0 and bool(result.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def latest_backup(backup_dir: str | Path, prefix: str) -> Path | None:
    """Retourne le backup le plus récent du répertoire, ou None."""
    d = Path(backup_dir)
    if not d.exists():
        return None
    backups = sorted(d.glob(f"{prefix}-*.backup"))
    return backups[-1] if backups else None


def apply_retention(backup_dir: str | Path, prefix: str, retention_days: int) -> list[Path]:
    """
    Supprime les backups plus vieux que retention_days. Retourne la liste
    des fichiers supprimés. Ne supprime jamais le plus récent (sécurité).
    """
    from datetime import timedelta
    d = Path(backup_dir)
    if not d.exists() or retention_days <= 0:
        return []
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    backups = sorted(d.glob(f"{prefix}-*.backup"))
    if len(backups) <= 1:
        return []  # toujours garder au moins un backup
    deleted: list[Path] = []
    for b in backups[:-1]:  # ne jamais toucher au plus récent
        mtime = datetime.fromtimestamp(b.stat().st_mtime, tz=UTC)
        if mtime < cutoff:
            b.unlink()
            deleted.append(b)
    return deleted


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL backup/restore — CodeRoute Guinée")
    parser.add_argument("--env-file",  help="Fichier .env à charger")
    parser.add_argument("--dry-run",   action="store_true", help="Simuler sans exécuter")
    parser.add_argument("--backup-dir", default=os.environ.get("BACKUP_DIR", "/var/backups/coderoute"))
    parser.add_argument("--prefix",    default="coderoute-guinee")
    parser.add_argument("--verify",    action="store_true",
                        help="Vérifier l'intégrité du dernier backup (sans en créer)")
    parser.add_argument("--retention-days", type=int, default=0,
                        help="Supprimer les backups plus vieux que N jours après création")

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

    # ── Mode vérification (--verify) : contrôle l'intégrité du dernier backup ──
    if getattr(args, "verify", False):
        target = latest_backup(args.backup_dir, args.prefix)
        if target is None:
            print("❌ Aucun backup à vérifier dans", args.backup_dir, file=sys.stderr)
            return 1
        ok = verify_backup_file(target)
        print(f"{'✅' if ok else '❌'} Vérification {target.name} : {'valide' if ok else 'CORROMPU'}")
        return 0 if ok else 1

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
        if result.returncode != 0:
            print("❌ pg_dump a échoué", file=sys.stderr)
            return result.returncode

        # Vérifier immédiatement l'intégrité du backup créé
        if verify_backup_file(dest):
            print(f"✅ Backup vérifié : {dest.name} ({dest.stat().st_size} octets)")
        else:
            print("❌ Le backup créé est illisible (vérification échouée)", file=sys.stderr)
            return 1

        # Appliquer la rétention (supprime les anciens, garde toujours le dernier)
        if args.retention_days > 0:
            deleted = apply_retention(args.backup_dir, args.prefix, args.retention_days)
            if deleted:
                print(f"🧹 Rétention : {len(deleted)} ancien(s) backup(s) supprimé(s)")
        return 0


if __name__ == "__main__":
    sys.exit(main())

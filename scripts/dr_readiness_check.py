#!/usr/bin/env python3
"""
Vérification de l'état de préparation à la reprise (DR readiness)
================================================================

Contrôle automatiquement que les éléments du Plan de Reprise après Sinistre
(docs/plan_reprise_sinistre.md) sont opérationnels :

  1. Un backup récent existe et est valide (restaurable)
  2. La chaîne d'audit est intacte (données sensibles non altérées)
  3. La base répond et le schéma est complet

À exécuter régulièrement (idéalement en CI quotidienne, après le backup) et
lors des exercices de reprise à froid. Retourne un code de sortie non nul
si un élément critique manque — permet d'alerter automatiquement.

Usage :
  DATABASE_URL="postgresql+psycopg://..." \
    python scripts/dr_readiness_check.py --backup-dir /var/backups/coderoute
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _check_backup(backup_dir: str, prefix: str, max_age_hours: int) -> tuple[bool, str]:
    """Un backup récent et valide existe-t-il ?"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from postgres_backup import latest_backup, verify_backup_file
    except ImportError:
        return False, "module postgres_backup introuvable"

    latest = latest_backup(backup_dir, prefix)
    if latest is None:
        return False, f"aucun backup dans {backup_dir}"

    age = datetime.now(UTC) - datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC)
    if age > timedelta(hours=max_age_hours):
        return False, f"backup trop ancien ({age.total_seconds()/3600:.0f}h > {max_age_hours}h)"

    if not verify_backup_file(latest):
        return False, f"backup corrompu : {latest.name}"

    return True, f"backup valide {latest.name} (âge {age.total_seconds()/3600:.1f}h)"


def _check_audit_chain() -> tuple[bool, str]:
    """La chaîne d'audit est-elle intacte ?"""
    try:
        from app.audit_chain import verify_audit_chain
        from app.db.session import SessionLocal
    except ImportError as exc:
        return False, f"import impossible : {exc}"

    db = SessionLocal()
    try:
        rep = verify_audit_chain(db)
    finally:
        db.close()

    if rep["valid"]:
        return True, f"chaîne intacte ({rep['total_entries']} entrées)"
    return False, f"chaîne ROMPUE au seq {rep['broken_at_seq']} : {rep['reason']}"


def _check_database() -> tuple[bool, str]:
    """La base répond-elle et le schéma est-il complet ?"""
    try:
        from sqlalchemy import inspect, text
        from app.db.session import SessionLocal
        from app.routers.health import CRITICAL_TABLES
    except ImportError as exc:
        return False, f"import impossible : {exc}"

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        tables = set(inspect(db.bind).get_table_names())
        missing = sorted(CRITICAL_TABLES - tables)
        if missing:
            return False, f"tables critiques manquantes : {missing}"
        return True, "base OK, schéma complet"
    except Exception as exc:  # noqa: BLE001
        return False, f"base inaccessible : {exc.__class__.__name__}"
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Vérification DR readiness")
    parser.add_argument("--backup-dir", default=os.environ.get("BACKUP_DIR", "/var/backups/coderoute"))
    parser.add_argument("--prefix", default="coderoute-guinee")
    parser.add_argument("--max-age-hours", type=int, default=26,
                        help="Âge max acceptable du dernier backup (défaut 26h)")
    parser.add_argument("--skip-backup", action="store_true",
                        help="Ignorer la vérification backup (ex. en environnement de test)")
    args = parser.parse_args()

    print("=== Vérification de l'état de reprise (DR readiness) ===\n")
    checks: list[tuple[str, bool, str]] = []

    if not args.skip_backup:
        ok, msg = _check_backup(args.backup_dir, args.prefix, args.max_age_hours)
        checks.append(("Backup récent et valide", ok, msg))

    ok, msg = _check_audit_chain()
    checks.append(("Chaîne d'audit intacte", ok, msg))

    ok, msg = _check_database()
    checks.append(("Base et schéma", ok, msg))

    all_ok = True
    for name, ok, msg in checks:
        symbol = "✅" if ok else "❌"
        print(f"  {symbol} {name} : {msg}")
        all_ok = all_ok and ok

    print()
    if all_ok:
        print("✅ Prêt pour la reprise : tous les contrôles sont au vert.")
        return 0
    print("❌ NON PRÊT : au moins un contrôle critique a échoué (voir ci-dessus).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

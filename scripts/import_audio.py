#!/usr/bin/env python3
"""
Import en masse des enregistrements audio en langues nationales
===============================================================

Associe des fichiers audio (enregistrés par des locuteurs natifs) aux
questions d'examen, langue par langue.

RAPPEL DE CONCEPTION : seul l'ORAL est en langue nationale. Le texte des
questions reste affiché en français. Le candidat VOIT en français et
ENTEND dans sa langue.

--- Deux modes d'utilisation ---

1) Depuis un dossier de fichiers (convention de nommage)

   Organisez les fichiers ainsi :
       audio/ff/<numero_question>.mp3      (Pular)
       audio/man/<numero_question>.mp3     (Malinké)
       audio/sus/<numero_question>.mp3     (Soussou)

   Puis :
       python scripts/import_audio.py --from-dir ./audio --base-url /audio

   Le numéro correspond à l'ordre des questions officielles (1, 2, 3…),
   ou à l'identifiant exact de la question.

2) Depuis un fichier CSV (contrôle fin)

   CSV avec les colonnes : question_id,langue,url
       q-abc123,ff,https://cdn.example.gn/audio/ff/q1.mp3
       q-abc123,man,/audio/man/q1.mp3

   Puis :
       python scripts/import_audio.py --from-csv enregistrements.csv

--- Options utiles ---
   --dry-run    : simule sans rien écrire (à faire en premier)
   --report     : affiche la couverture audio actuelle et s'arrête
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

# Langues nationales acceptées (le français n'a pas besoin d'enregistrement)
LANGUAGES = {"ff": "Pular", "man": "Malinké", "sus": "Soussou",
             "kss": "Kissi", "gkp": "Kpelle", "lom": "Toma"}


def _setup():
    """Prépare l'accès à la base (à appeler après les imports d'app)."""
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("SECRET_KEY", "import-audio-1234567890abcdefgh")
    os.environ.setdefault("CSRF_SECRET", "import-audio-1234567890abcdefgh")


def _valid_url(url: str) -> bool:
    return url.startswith("https://") or url.startswith("/audio/")


def report_coverage(db) -> None:
    """Affiche la couverture audio : combien de questions enregistrées par langue."""
    from app.models_question import Question
    from sqlalchemy import select

    questions = list(db.scalars(
        select(Question).where(Question.is_active.is_(True))
    ).all())
    total = len(questions)
    print(f"\n=== Couverture audio ({total} questions actives) ===\n")

    for code, name in LANGUAGES.items():
        n = sum(
            1 for q in questions
            if isinstance(q.translations, dict)
            and isinstance(q.translations.get(code), dict)
            and q.translations[code].get("audio_url")
        )
        pct = (n / total * 100) if total else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {name:10s} [{bar}] {n:3d}/{total}  ({pct:.0f}%)")

    print("\nLes questions sans enregistrement utilisent la synthèse vocale "
          "(repli automatique) — aucune n'est jamais muette.\n")


def import_from_csv(db, csv_path: str, dry_run: bool) -> tuple[int, int]:
    from app.models_question import Question

    applied = skipped = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            qid = (row.get("question_id") or "").strip()
            lang = (row.get("langue") or row.get("lang") or "").strip()
            url = (row.get("url") or "").strip()

            if lang not in LANGUAGES:
                print(f"  ⨯ langue inconnue '{lang}' (ligne ignorée)"); skipped += 1; continue
            if not _valid_url(url):
                print(f"  ⨯ URL invalide '{url[:40]}' (https:// ou /audio/ requis)"); skipped += 1; continue

            q = db.get(Question, qid)
            if not q:
                print(f"  ⨯ question introuvable : {qid}"); skipped += 1; continue

            tr = dict(q.translations or {})
            tr[lang] = {"audio_url": url}
            if not dry_run:
                q.translations = tr
                db.add(q)
            applied += 1
            print(f"  ✓ {LANGUAGES[lang]:10s} → {qid[:12]}…  {url[:45]}")

    if not dry_run:
        db.commit()
    return applied, skipped


def import_from_dir(db, root: str, base_url: str, dry_run: bool) -> tuple[int, int]:
    """
    Parcourt audio/<langue>/<n>.mp3 et associe aux questions par ordre
    (n = 1 correspond à la 1re question active, etc.) ou par identifiant
    si le nom du fichier correspond à un id de question.
    """
    from app.models_question import Question
    from sqlalchemy import select

    questions = list(db.scalars(
        select(Question).where(Question.is_active.is_(True)).order_by(Question.created_at.asc())
    ).all())
    by_index = {str(i + 1): q for i, q in enumerate(questions)}
    by_id = {q.id: q for q in questions}

    applied = skipped = 0
    root_path = Path(root)
    for lang in LANGUAGES:
        lang_dir = root_path / lang
        if not lang_dir.is_dir():
            continue
        for audio_file in sorted(lang_dir.glob("*.mp3")):
            stem = audio_file.stem
            q = by_id.get(stem) or by_index.get(stem)
            if not q:
                print(f"  ⨯ aucune question pour '{audio_file.name}' (langue {lang})")
                skipped += 1
                continue
            url = f"{base_url.rstrip('/')}/{lang}/{audio_file.name}"
            if not _valid_url(url):
                print(f"  ⨯ URL construite invalide : {url}"); skipped += 1; continue

            tr = dict(q.translations or {})
            tr[lang] = {"audio_url": url}
            if not dry_run:
                q.translations = tr
                db.add(q)
            applied += 1
            print(f"  ✓ {LANGUAGES[lang]:10s} → {audio_file.name}  →  {url}")

    if not dry_run:
        db.commit()
    return applied, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Import des enregistrements audio")
    parser.add_argument("--from-dir", help="Dossier contenant audio/<langue>/*.mp3")
    parser.add_argument("--base-url", default="/audio",
                        help="Préfixe des URL servies (défaut /audio)")
    parser.add_argument("--from-csv", help="CSV : question_id,langue,url")
    parser.add_argument("--report", action="store_true", help="Afficher la couverture et quitter")
    parser.add_argument("--dry-run", action="store_true", help="Simuler sans écrire")
    args = parser.parse_args()

    _setup()
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        if args.report:
            report_coverage(db)
            return 0

        if not args.from_dir and not args.from_csv:
            parser.error("préciser --from-dir, --from-csv ou --report")

        if args.dry_run:
            print("\n[SIMULATION] Aucune écriture ne sera effectuée.\n")

        if args.from_csv:
            applied, skipped = import_from_csv(db, args.from_csv, args.dry_run)
        else:
            applied, skipped = import_from_dir(db, args.from_dir, args.base_url, args.dry_run)

        print(f"\n{'[SIMULATION] ' if args.dry_run else ''}"
              f"{applied} enregistrement(s) associé(s), {skipped} ignoré(s).")
        if not args.dry_run and applied:
            report_coverage(db)
        return 0 if skipped == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

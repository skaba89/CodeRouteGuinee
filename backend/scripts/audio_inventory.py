#!/usr/bin/env python3
"""
Générateur d'inventaire audio — CodeRoute Guinée
Usage:
  python scripts/audio_inventory.py
  python scripts/audio_inventory.py --locale ff
  python scripts/audio_inventory.py --export csv > todo.csv
"""
from __future__ import annotations
import argparse, csv, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
STATIC_AUDIO = Path(__file__).parent.parent / "static" / "audio"
LOCALES = {
    "ff": "Pular", "man": "Malinké", "sus": "Soussou",
    "kss": "Kissi", "gkp": "Kpelle", "lom": "Toma",
    "fr": "Français", "en": "English",
}

def get_questions() -> list[dict]:
    os.environ.setdefault("AUTO_CREATE_TABLES", "false")
    try:
        from app.db.session import SessionLocal
        from app.models_question import Question
        from sqlalchemy import select
        db = SessionLocal()
        try:
            rows = db.scalars(select(Question).where(Question.is_active.is_(True)).order_by(Question.category)).all()
            return [{"id": q.id, "category": q.category, "text": q.text[:60]} for q in rows]
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ DB indisponible: {e}", file=sys.stderr)
        return []

def get_existing(locale: str) -> set[str]:
    d = STATIC_AUDIO / locale
    return {f.stem for f in d.glob("*.mp3")} if d.exists() else set()

def print_report(questions: list[dict], locale_filter: str | None) -> None:
    total = len(questions)
    print(f"\n{'═'*60}\n  INVENTAIRE AUDIO — CodeRoute Guinée ({total} questions)\n{'═'*60}\n")
    for code, name in LOCALES.items():
        if locale_filter and code != locale_filter: continue
        ex = get_existing(code)
        covered = sum(1 for q in questions if q["id"] in ex)
        pct = covered / total * 100 if total else 0
        bar = "█" * int(pct/5) + "░" * (20-int(pct/5))
        icon = "✅" if pct >= 100 else ("🟡" if pct >= 50 else "❌")
        print(f"  {icon} {code:3} {name:<12} [{bar}] {covered:>5}/{total} ({pct:5.1f}%)")
    print(f"\n  Upload : POST /api/v1/audio/upload/{{locale}}/{{question_id}}")
    print(f"  Check  : GET  /api/v1/audio/inventory\n")

def export_csv(questions: list[dict], locale_filter: str | None) -> None:
    w = csv.writer(sys.stdout)
    w.writerow(["locale", "langue", "question_id", "categorie", "texte_fr", "statut"])
    for code, name in LOCALES.items():
        if locale_filter and code != locale_filter: continue
        ex = get_existing(code)
        for q in questions:
            w.writerow([code, name, q["id"], q["category"], q["text"],
                        "EXISTE" if q["id"] in ex else "MANQUANT"])

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--locale")
    p.add_argument("--export", choices=["csv"])
    args = p.parse_args()
    questions = get_questions()
    if args.export == "csv":
        export_csv(questions, args.locale)
    else:
        print_report(questions, args.locale)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only inventory of CodeRoute question media.

This script does not mutate questions, validation state, storage or media files.
It inventories the legacy Question.media_* fields and highlights the main gaps
that must be resolved before the premium MediaAsset migration.

Usage from repository root:
    python scripts/audit_media_library.py
    python scripts/audit_media_library.py --json media-audit.json
    python scripts/audit_media_library.py --probe-remote --json media-audit.json

Remote probing is optional and only attempts HEAD requests after the existing
CodeRoute media URL policy accepts the URL. It never follows credentials or
private/internal hosts. Resolution/duration cannot be proven from the current
Question schema and are therefore reported as unknown until MediaAsset exists.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.media_policy import validate_media_url  # noqa: E402
from app.models_question import Question  # noqa: E402

LEGACY_TYPES = {"sign", "scene"}
REAL_TYPES = {"image", "video"}
KNOWN_TYPES = LEGACY_TYPES | REAL_TYPES


def _looks_remote(value: str | None) -> bool:
    return bool(value and value.lower().startswith(("https://", "http://")))


def _semantic_status(text: str, media: str | None) -> tuple[str | None, str | None]:
    """Detect only high-confidence legacy mismatches; do not guess correctness."""
    t = (text or "").lower()
    m = (media or "").lower()

    rules = [
        (("passage à niveau" in t), ("rail" in m or "train" in m), "passage à niveau sans scène ferroviaire"),
        (("verglas" in t), ("slipper" in m or "ice" in m or "verglas" in m), "verglas représenté par une scène sans chaussée glissante"),
        (("pluie" in t or "brouillard" in t), ("rain" in m or "fog" in m or "weather" in m), "météo dégradée sans scène météo dédiée"),
        (("somnolence" in t or "fatigue" in t), ("night" in m or "fatigue" in m or "drows" in m), "fatigue/somnolence sans média dédié"),
        (("feu orange" in t), ("traffic_light_orange" in m), "feu orange avec visuel non orange"),
        (("feu vert" in t and "piéton" in t), ("pedestrian" in m or "traffic_light_green" in m), "feu vert piéton avec média non dédié"),
        (("écoconduite" in t or "pollution" in t), ("eco" in m or "pollution" in m or "environment" in m), "écoconduite avec média non dédié"),
    ]
    for applies, valid, reason in rules:
        if applies and not valid:
            return "REJECTED", reason
    return None, None


def _probe(url: str, media_type: str | None, timeout: float) -> dict[str, Any]:
    if media_type not in REAL_TYPES:
        return {"http_status": None, "content_type": None, "content_length": None, "probe_error": None}
    try:
        safe_url = validate_media_url(url, media_type)
    except ValueError as exc:
        return {"http_status": None, "content_type": None, "content_length": None, "probe_error": str(exc)}

    req = Request(safe_url, method="HEAD", headers={"User-Agent": "CodeRoute-Media-Audit/1.0"})
    try:
        with urlopen(req, timeout=timeout) as response:  # noqa: S310 - URL validated by project policy
            return {
                "http_status": int(getattr(response, "status", response.getcode())),
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
                "probe_error": None,
            }
    except HTTPError as exc:
        return {"http_status": int(exc.code), "content_type": None, "content_length": None, "probe_error": f"HTTP {exc.code}"}
    except (URLError, TimeoutError, OSError) as exc:
        return {"http_status": None, "content_type": None, "content_length": None, "probe_error": exc.__class__.__name__}


def classify(question: Question) -> tuple[str, list[str]]:
    reasons: list[str] = []
    media_type = (question.media_type or "").strip().lower() or None
    media_url = (question.media_url or "").strip() or None

    if not media_url:
        return "MISSING", ["question sans média"]

    if media_type not in KNOWN_TYPES:
        return "REJECTED", [f"type média inconnu: {media_type!r}"]

    semantic_status, semantic_reason = _semantic_status(question.text, media_url)
    if semantic_status:
        reasons.append(semantic_reason or "mapping sémantique incohérent")
        return semantic_status, reasons

    if media_type in LEGACY_TYPES:
        reasons.append("illustration SVG legacy/synthétique à revoir pour une expérience examen premium")
        if not (question.media_alt or "").strip():
            reasons.append("alt manquant")
        return "REVIEW_REQUIRED", reasons

    if not _looks_remote(media_url):
        return "BROKEN", ["image/vidéo réelle sans URL HTTP(S)"]

    try:
        validate_media_url(media_url, media_type)
    except ValueError as exc:
        return "BROKEN", [f"URL refusée par la politique média: {exc}"]

    # The current schema has no provenance/license fields, therefore a real
    # remote media URL cannot be certified copyright-safe from Question alone.
    reasons.append("provenance/licence non démontrable dans le schéma Question actuel")
    if not (question.media_alt or "").strip():
        reasons.append("alt manquant")
    return "COPYRIGHT_UNKNOWN", reasons


def build_report(*, probe_remote: bool, timeout: float) -> dict[str, Any]:
    with SessionLocal() as db:
        questions = list(db.scalars(select(Question).order_by(Question.category, Question.created_at)).all())

    statuses: Counter[str] = Counter()
    types: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []

    for question in questions:
        status, reasons = classify(question)
        statuses[status] += 1
        media_type = (question.media_type or "none").lower()
        types[media_type] += 1
        categories[question.category] += 1

        row: dict[str, Any] = {
            "question_id": question.id,
            "category": question.category,
            "text": question.text,
            "media_type": question.media_type,
            "media_url": question.media_url,
            "media_alt": question.media_alt,
            "validation_status": question.validation_status,
            "is_active": question.is_active,
            "audit_status": status,
            "reasons": reasons,
            "mime_type": None,
            "file_size_bytes": None,
            "width": None,
            "height": None,
            "duration_seconds": None,
            "thumbnail_present": None,
            "explanation_media_present": None,
            "source": None,
            "license": None,
            "last_media_validation": None,
        }
        if probe_remote and question.media_url and _looks_remote(question.media_url):
            probe = _probe(question.media_url, question.media_type, timeout)
            row.update(probe)
            row["mime_type"] = probe.get("content_type")
            try:
                row["file_size_bytes"] = int(probe["content_length"]) if probe.get("content_length") else None
            except (TypeError, ValueError):
                row["file_size_bytes"] = None
        rows.append(row)

    total = len(rows)
    active = sum(1 for row in rows if row["is_active"])
    approved = sum(1 for row in rows if row["validation_status"] == "approved")
    real = sum(1 for row in rows if row["media_type"] in REAL_TYPES)
    legacy = sum(1 for row in rows if row["media_type"] in LEGACY_TYPES)

    return {
        "schema": "coderoute_media_audit_v1",
        "read_only": True,
        "summary": {
            "questions_total": total,
            "questions_active": active,
            "questions_approved": approved,
            "real_image_or_video": real,
            "legacy_sign_or_scene": legacy,
            "premium_real_media_percent": round(real / total * 100, 1) if total else 0.0,
            "by_media_type": dict(sorted(types.items())),
            "by_audit_status": dict(sorted(statuses.items())),
            "by_category": dict(sorted(categories.items())),
        },
        "schema_gaps": [
            "source/provenance absente",
            "licence/copyright absent",
            "checksum_sha256 absent",
            "dimensions absentes",
            "duration absente",
            "poster/fallback non persistés",
            "explanation media non modélisé",
            "quality_status média absent",
            "regulatory_status média absent",
            "historique de validation média absent",
        ],
        "questions": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit read-only de la médiathèque questions CodeRoute")
    parser.add_argument("--json", dest="json_path", help="Écrire le rapport JSON dans ce fichier")
    parser.add_argument("--probe-remote", action="store_true", help="Faire des HEAD HTTPS sur les vraies URLs image/video")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout par média distant (défaut 5 s)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0 or args.timeout > 30:
        print("ERROR: --timeout doit être > 0 et <= 30", file=sys.stderr)
        return 2

    report = build_report(probe_remote=bool(args.probe_remote), timeout=float(args.timeout))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2, sort_keys=True))

    if args.json_path:
        path = Path(args.json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Rapport détaillé: {path}")

    # Audit only: never fail because media are currently non-premium.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

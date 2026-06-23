"""
Tarifs dynamiques — CodeRoute Guinée

Les tarifs d'examen et autres frais sont configurables par le super-admin
sans toucher le code. Stockage en base + cache mémoire LRU.

Tarifs par défaut (en GNF) :
  examen_code_B        : 150 000 GNF (permis B — voitures)
  examen_code_A        : 100 000 GNF (permis A — motos)
  examen_code_C        : 200 000 GNF (permis C — poids lourds)
  examen_code_D        : 200 000 GNF (permis D — transport en commun)
  frais_reinscription  : 50 000 GNF  (2ème tentative)
  frais_rattrapage     : 30 000 GNF  (3ème tentative et plus)
"""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

log = logging.getLogger("coderoute.tarifs")

# ── Tarifs par défaut ─────────────────────────────────────────────────────────

DEFAULT_TARIFS: dict[str, dict[str, Any]] = {
    "examen_code_B": {
        "libelle":          "Examen du code de la route — Permis B (voitures)",
        "montant_gnf":      150_000,
        "categorie_permis": "B",
        "description":      "Frais d'examen théorique pour l'obtention du permis de conduire catégorie B",
    },
    "examen_code_A": {
        "libelle":          "Examen du code de la route — Permis A (motos)",
        "montant_gnf":      100_000,
        "categorie_permis": "A",
        "description":      "Frais d'examen théorique pour l'obtention du permis de conduire catégorie A",
    },
    "examen_code_C": {
        "libelle":          "Examen du code de la route — Permis C (poids lourds)",
        "montant_gnf":      200_000,
        "categorie_permis": "C",
        "description":      "Frais d'examen théorique pour le permis poids lourds",
    },
    "examen_code_D": {
        "libelle":          "Examen du code de la route — Permis D (transport en commun)",
        "montant_gnf":      200_000,
        "categorie_permis": "D",
        "description":      "Frais d'examen théorique pour le transport en commun",
    },
    "frais_reinscription": {
        "libelle":          "Frais de réinscription (2ème tentative)",
        "montant_gnf":      50_000,
        "categorie_permis": None,
        "description":      "Frais applicables à partir de la 2ème tentative d'examen",
    },
    "frais_rattrapage": {
        "libelle":          "Frais de rattrapage (3ème tentative et plus)",
        "montant_gnf":      30_000,
        "categorie_permis": None,
        "description":      "Tarif réduit applicable à partir de la 3ème tentative",
    },
}

# ── Cache ─────────────────────────────────────────────────────────────────────

_cache: dict[str, dict] = {}
_cache_at: float = 0.0
_CACHE_TTL = 300   # 5 minutes


def _invalidate_cache() -> None:
    global _cache, _cache_at
    _cache = {}
    _cache_at = 0.0
    log.info("Cache tarifs invalidé")


# ── Table ─────────────────────────────────────────────────────────────────────

def _ensure_table(db: Session) -> None:
    """Crée la table tarifs si elle n'existe pas + insère les défauts."""
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS tarifs (
                cle              VARCHAR(80) PRIMARY KEY,
                libelle          VARCHAR(200) NOT NULL,
                montant_gnf      INTEGER NOT NULL CHECK (montant_gnf > 0),
                categorie_permis VARCHAR(10),
                description      TEXT,
                actif            BOOLEAN NOT NULL DEFAULT TRUE,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()

        # Insérer les tarifs par défaut s'ils n'existent pas
        for cle, t in DEFAULT_TARIFS.items():
            existing = db.execute(
                text("SELECT cle FROM tarifs WHERE cle = :cle"),
                {"cle": cle}
            ).fetchone()
            if not existing:
                db.execute(
                    text("""
                        INSERT INTO tarifs (cle, libelle, montant_gnf, categorie_permis, description)
                        VALUES (:cle, :lib, :montant, :cat, :desc)
                    """),
                    {
                        "cle":     cle,
                        "lib":     t["libelle"],
                        "montant": t["montant_gnf"],
                        "cat":     t["categorie_permis"],
                        "desc":    t["description"],
                    }
                )
        db.commit()
    except Exception as e:
        db.rollback()
        log.warning("Erreur init table tarifs : %s", e)


# ── API publique ──────────────────────────────────────────────────────────────

def get_tarif(cle: str, db: Session | None = None) -> int:
    """
    Retourne le montant GNF pour une clé de tarif.
    Utilise le cache (TTL 5 min) puis la DB, puis la valeur par défaut.
    """
    global _cache, _cache_at

    # Cache valide
    if _cache and time.time() - _cache_at < _CACHE_TTL and cle in _cache:
        return _cache[cle]["montant_gnf"]

    # Charger depuis la DB
    _db = db or SessionLocal()
    try:
        _ensure_table(_db)
        rows = _db.execute(
            text("SELECT cle, montant_gnf, libelle, categorie_permis, description, actif FROM tarifs")
        ).fetchall()
        _cache = {
            r[0]: {
                "montant_gnf":      r[1],
                "libelle":          r[2],
                "categorie_permis": r[3],
                "description":      r[4],
                "actif":            bool(r[5]),
            }
            for r in rows
        }
        _cache_at = time.time()
    except Exception as e:
        log.error("Erreur chargement tarifs : %s", e)
    finally:
        if db is None:
            _db.close()

    if cle in _cache:
        return _cache[cle]["montant_gnf"]

    # Fallback valeur par défaut
    default = DEFAULT_TARIFS.get(cle)
    if default:
        return default["montant_gnf"]

    raise ValueError(f"Tarif inconnu : {cle}")


def get_all_tarifs(db: Session) -> list[dict]:
    """Retourne tous les tarifs actifs."""
    _ensure_table(db)
    rows = db.execute(
        text("SELECT cle, libelle, montant_gnf, categorie_permis, description, actif FROM tarifs ORDER BY cle")
    ).fetchall()
    return [
        {
            "cle":              r[0],
            "libelle":          r[1],
            "montant_gnf":      r[2],
            "categorie_permis": r[3],
            "description":      r[4],
            "actif":            bool(r[5]),
        }
        for r in rows
    ]


def update_tarif(cle: str, montant_gnf: int, db: Session) -> dict:
    """Met à jour un tarif. Invalide le cache."""
    _ensure_table(db)
    if montant_gnf < 1_000 or montant_gnf > 10_000_000:
        raise ValueError("Montant invalide (1 000 ≤ montant ≤ 10 000 000 GNF)")

    existing = db.execute(text("SELECT cle FROM tarifs WHERE cle=:cle"), {"cle": cle}).fetchone()
    if not existing:
        raise ValueError(f"Clé de tarif inconnue : {cle}")

    db.execute(
        text("UPDATE tarifs SET montant_gnf=:m, updated_at=CURRENT_TIMESTAMP WHERE cle=:cle"),
        {"m": montant_gnf, "cle": cle}
    )
    db.commit()
    _invalidate_cache()
    log.info("Tarif %s mis à jour : %d GNF", cle, montant_gnf)
    return {"cle": cle, "montant_gnf": montant_gnf, "updated": True}


def get_tarif_for_candidate(permit_category: str, attempt_number: int = 1) -> int:
    """
    Calcule le tarif applicable pour un candidat selon :
    - La catégorie de permis
    - Le numéro de tentative (1 = premier passage, 2 = réinscription, 3+ = rattrapage)
    """
    if attempt_number >= 3:
        return get_tarif("frais_rattrapage")
    if attempt_number == 2:
        base  = get_tarif(f"examen_code_{permit_category.upper()}")
        reinsc = get_tarif("frais_reinscription")
        return base + reinsc
    # 1ère tentative
    return get_tarif(f"examen_code_{permit_category.upper()}")

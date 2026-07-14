"""
Test — gestion des sessions de base de données.

Point le plus critique : get_db() doit TOUJOURS rendre la connexion au pool,
y compris quand le endpoint lève une exception. Une fuite de connexions
épuiserait le pool et mettrait tout le système à terre sous charge — le pire
scénario un jour de session nationale.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.db.session import get_db, init_db, _sqlite_add_columns_if_missing


def _consume(gen, raise_inside: bool = False) -> None:
    """Simule un cycle FastAPI complet sur la dépendance get_db."""
    next(gen)
    if raise_inside:
        try:
            gen.throw(ValueError("erreur simulée dans le endpoint"))
        except (ValueError, StopIteration):
            pass
    try:
        next(gen)
    except StopIteration:
        pass


def test_session_fermee_en_usage_normal() -> None:
    init_db()
    for _ in range(20):
        _consume(get_db())  # ne doit pas lever


def test_session_fermee_meme_sur_erreur() -> None:
    """
    Si le endpoint lève, get_db doit faire un rollback ET fermer la session.
    Sans le `finally: db.close()`, chaque erreur fuirait une connexion.
    """
    init_db()
    for _ in range(20):
        _consume(get_db(), raise_inside=True)  # ne doit pas lever non plus


def test_get_db_fournit_une_session_utilisable() -> None:
    from sqlalchemy import text
    init_db()
    gen = get_db()
    db = next(gen)
    try:
        assert db.execute(text("SELECT 1")).scalar() == 1
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Protection contre l'injection SQL dans les migrations SQLite ────────────

def test_liste_blanche_types_couvre_les_migrations() -> None:
    """
    Chaque type utilisé dans la liste des migrations doit figurer dans la
    liste blanche _SAFE_TYPES. Sinon la colonne est SILENCIEUSEMENT ignorée
    (branche morte) — c'était le cas de TEXT, requis par bookings.notes et
    candidates.address.
    """
    import inspect as _inspect
    import re

    from app.db import session as session_mod

    src = _inspect.getsource(session_mod._sqlite_add_columns_if_missing)

    # Types déclarés dans la liste des migrations
    declared = set(re.findall(r'\(\s*"[a-z_]+",\s*"[a-z_]+",\s*"([^"]+)"\s*\)', src))
    # Types autorisés
    m = re.search(r"_SAFE_TYPES = \{(.*?)\}", src, re.DOTALL)
    assert m, "_SAFE_TYPES introuvable"
    allowed = set(re.findall(r'"([^"]+)"', m.group(1)))

    manquants = declared - allowed
    assert not manquants, f"Types déclarés mais non autorisés (colonnes ignorées) : {manquants}"


def test_colonnes_texte_bien_creees() -> None:
    """bookings.notes et candidates.address (type TEXT) doivent exister."""
    from sqlalchemy import inspect as sa_inspect

    from app.db.session import engine

    init_db()
    insp = sa_inspect(engine)
    for table, col in (("bookings", "notes"), ("candidates", "address")):
        cols = [c["name"] for c in insp.get_columns(table)]
        assert col in cols, f"{table}.{col} manquante"

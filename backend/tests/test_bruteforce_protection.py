"""
Test — protection contre la force brute sur le login.

Point clé vérifié par l'audit : le compteur de tentatives est stocké en BASE
(et non en mémoire du processus). Avec plusieurs workers gunicorn, un
compteur en mémoire serait trivialement contournable — il suffirait de
tomber sur un autre worker pour repartir de zéro.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import init_db, SessionLocal
from app.auth_guard import LoginRateLimiter


def test_blocage_apres_trop_de_tentatives() -> None:
    init_db()
    db = SessionLocal()
    try:
        limiter = LoginRateLimiter(max_attempts=3, window_seconds=300)
        key = f"test-{uuid.uuid4().hex[:8]}"

        assert limiter.is_blocked(key, db) is False
        for _ in range(3):
            limiter.register_failure(key, db)
        assert limiter.is_blocked(key, db) is True
    finally:
        db.close()


def test_reset_debloque() -> None:
    init_db()
    db = SessionLocal()
    try:
        limiter = LoginRateLimiter(max_attempts=2, window_seconds=300)
        key = f"test-{uuid.uuid4().hex[:8]}"
        limiter.register_failure(key, db)
        limiter.register_failure(key, db)
        assert limiter.is_blocked(key, db) is True

        limiter.reset(key, db)  # connexion réussie → compteur remis à zéro
        assert limiter.is_blocked(key, db) is False
    finally:
        db.close()


def test_compteur_partage_entre_instances() -> None:
    """
    Deux instances distinctes du limiteur (= deux workers gunicorn) partagent
    le même compteur via la base. Un attaquant ne peut donc PAS contourner le
    blocage en tombant sur un autre worker.
    """
    init_db()
    db = SessionLocal()
    try:
        key = f"test-{uuid.uuid4().hex[:8]}"
        worker_1 = LoginRateLimiter(max_attempts=3, window_seconds=300)
        worker_2 = LoginRateLimiter(max_attempts=3, window_seconds=300)

        # Le worker 1 enregistre les 3 échecs
        for _ in range(3):
            worker_1.register_failure(key, db)

        # Le worker 2 — instance différente, mémoire différente — voit le blocage
        assert worker_2.is_blocked(key, db) is True
    finally:
        db.close()


def test_login_renvoie_429_apres_echecs_repetes() -> None:
    """Bout en bout : l'API renvoie 429 après trop d'échecs."""
    init_db()
    email = f"brute-{uuid.uuid4().hex[:8]}@test.gn"
    with TestClient(app) as client:
        codes = []
        for _ in range(12):
            r = client.post("/api/v1/auth/login",
                            data={"username": email, "password": "MauvaisMotDePasse!"},
                            headers={"Content-Type": "application/x-www-form-urlencoded"})
            codes.append(r.status_code)
        # Au moins une réponse 429 (trop de tentatives) doit apparaître
        assert 429 in codes, f"aucun blocage anti-force-brute : {set(codes)}"

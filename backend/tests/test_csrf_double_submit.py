"""
Test — protection CSRF (pattern Double-Submit).

Le double-submit exige que le token du HEADER corresponde à celui du COOKIE.
Un site tiers peut forcer le navigateur à envoyer le cookie (c'est le
principe même du CSRF), mais il ne peut PAS le LIRE pour le recopier dans le
header (politique d'origine identique). Sans cette comparaison, la protection
serait illusoire : n'importe quel token signé suffirait.
"""
from __future__ import annotations

import time

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.requests import Request

from app.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    check_csrf,
    generate_csrf_token,
    verify_csrf_token,
)


def _request(method: str, path: str, header_token: str | None, cookie_token: str | None) -> Request:
    headers = []
    if header_token is not None:
        headers.append((CSRF_HEADER_NAME.encode(), header_token.encode()))
    if cookie_token is not None:
        headers.append((b"cookie", f"{CSRF_COOKIE_NAME}={cookie_token}".encode()))
    scope = {
        "type": "http", "method": method, "path": path,
        "headers": headers, "query_string": b"", "scheme": "https",
        "server": ("test", 443), "root_path": "",
    }
    return Request(scope)


# ── Génération / vérification du token ──────────────────────────────────────

def test_token_genere_est_valide() -> None:
    assert verify_csrf_token(generate_csrf_token()) is True


def test_token_falsifie_rejete() -> None:
    token = generate_csrf_token()
    rand, ts, _sig = token.split(".")
    assert verify_csrf_token(f"{rand}.{ts}.signaturebidon") is False


def test_token_malforme_rejete() -> None:
    assert verify_csrf_token("nimportequoi") is False
    assert verify_csrf_token("") is False
    assert verify_csrf_token("a.b") is False


def test_token_expire_rejete() -> None:
    from app.csrf import _sign
    vieux_ts = str(int(time.time()) - 7200)  # 2 h → au-delà du TTL (1 h)
    rand = "abc123"
    token = f"{rand}.{vieux_ts}.{_sign(f'{rand}.{vieux_ts}')}"
    assert verify_csrf_token(token) is False


# ── check_csrf : le cœur du double-submit ───────────────────────────────────

def test_requete_valide_header_et_cookie_correspondent() -> None:
    token = generate_csrf_token()
    check_csrf(_request("POST", "/api/v1/bookings", token, token))  # ne lève pas


def test_methode_non_mutative_exemptee() -> None:
    check_csrf(_request("GET", "/api/v1/bookings", None, None))  # ne lève pas


def test_chemin_exempte(  ) -> None:
    check_csrf(_request("POST", "/api/v1/auth/login", None, None))  # ne lève pas


def test_header_manquant_refuse() -> None:
    token = generate_csrf_token()
    with pytest.raises(HTTPException) as exc:
        check_csrf(_request("POST", "/api/v1/bookings", None, token))
    assert exc.value.status_code == 403


def test_cookie_manquant_refuse() -> None:
    token = generate_csrf_token()
    with pytest.raises(HTTPException) as exc:
        check_csrf(_request("POST", "/api/v1/bookings", token, None))
    assert exc.value.status_code == 403


def test_header_et_cookie_differents_refuses() -> None:
    """
    L'ATTAQUE CSRF typique : le navigateur envoie le cookie de la victime,
    mais l'attaquant ne peut pas le lire pour le recopier dans le header.
    Il met donc un autre token (valide en signature) → doit être REFUSÉ.
    """
    cookie_victime = generate_csrf_token()
    token_attaquant = generate_csrf_token()  # signé, mais ≠ cookie
    assert token_attaquant != cookie_victime

    with pytest.raises(HTTPException) as exc:
        check_csrf(_request("POST", "/api/v1/bookings", token_attaquant, cookie_victime))
    assert exc.value.status_code == 403
    assert "incohérent" in exc.value.detail.lower()


def test_token_invalide_dans_header_refuse() -> None:
    with pytest.raises(HTTPException):
        check_csrf(_request("POST", "/api/v1/bookings", "bidon", "bidon"))

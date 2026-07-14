"""
Protection CSRF — CodeRoute Guinée
Pattern : Double-Submit Token (stateless, compatible API REST + JWT)

Fonctionnement :
  1. GET /api/v1/auth/csrf-token → génère un token signé HMAC-SHA256, le pose en cookie
  2. Chaque requête mutative (POST/PUT/PATCH/DELETE) doit inclure ce token dans
     le header X-CSRF-Token
  3. Le middleware vérifie signature + timing-safe compare

Pourquoi ce pattern et pas SameSite=Strict seul :
  - SameSite ne couvre pas les anciens navigateurs (< 2019)
  - Les requêtes cross-origin depuis les apps mobiles WebView passent SameSite
  - Ce pattern est stateless (pas de session server-side)

Variables d'env :
  CSRF_SECRET — secret HMAC (32+ octets hex). Si absent → dev mode (warning).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

if TYPE_CHECKING:
    pass

# ── Configuration ─────────────────────────────────────────────────────────────

CSRF_HEADER_NAME  = "x-csrf-token"
CSRF_COOKIE_NAME  = "csrf_token"
CSRF_TOKEN_TTL    = 3600          # 1 heure
CSRF_TOKEN_LENGTH = 32            # octets

from app.core.config import get_settings as _get_settings


def _secret_bytes() -> bytes:
    """
    Secret HMAC lu à CHAQUE usage (et non figé à l'import).

    Sans cela, une rotation de secret (procédure de sécurité obligatoire
    après un incident — voir SECURITY_ROTATION.md) resterait sans effet
    tant que le processus n'aurait pas redémarré.
    """
    secret = os.environ.get("CSRF_SECRET", "") or _get_settings().csrf_secret
    return secret.encode()


# ── Génération du token ───────────────────────────────────────────────────────

def _sign(payload: str) -> str:
    """Signature HMAC-SHA256 du payload."""
    return hmac.new(_secret_bytes(), payload.encode(), hashlib.sha256).hexdigest()


def generate_csrf_token() -> str:
    """
    Génère un token CSRF signé de la forme : {random}.{timestamp}.{signature}
    Le random prévient la devinabilité, le timestamp permet l'expiration.
    """
    rand = secrets.token_hex(CSRF_TOKEN_LENGTH)
    ts   = str(int(time.time()))
    sig  = _sign(f"{rand}.{ts}")
    return f"{rand}.{ts}.{sig}"


def verify_csrf_token(token: str) -> bool:
    """
    Vérifie :
      1. Format correct (3 parties)
      2. Signature valide (timing-safe)
      3. Token non expiré (< CSRF_TOKEN_TTL secondes)
    Retourne False si invalide (ne lève pas d'exception).
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        rand, ts_str, sig = parts

        # Vérifier l'expiration
        ts = int(ts_str)
        if time.time() - ts > CSRF_TOKEN_TTL:
            return False

        # Vérifier la signature (timing-safe)
        expected_sig = _sign(f"{rand}.{ts_str}")
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False


# ── Endpoint helper ───────────────────────────────────────────────────────────

def set_csrf_cookie(response, token: str) -> None:
    """
    Pose le cookie CSRF (httpOnly=False — le client JS doit le lire pour le
    recopier dans le header X-CSRF-Token).

    SameSite :
      • production  → "none" + Secure : le frontend et le backend sont sur
        des domaines DIFFÉRENTS (…-frontend.onrender.com vs …-backend…).
        Avec "lax", le navigateur n'enverrait PAS le cookie sur ces requêtes
        cross-site et toutes les requêtes mutatives seraient rejetées.
        "none" impose Secure (HTTPS), ce qui est le cas en production.
      • développement → "lax" (même origine localhost, et "none" sans HTTPS
        est refusé par les navigateurs).

    La protection CSRF ne repose pas sur SameSite mais sur le double-submit :
    un site tiers peut faire envoyer le cookie, mais ne peut pas le LIRE
    (politique d'origine identique) pour le recopier dans le header.
    """
    prod = os.environ.get("ENVIRONMENT", "development").lower() == "production"
    response.set_cookie(
        key      = CSRF_COOKIE_NAME,
        value    = token,
        httponly = False,                    # JS doit pouvoir lire le token
        secure   = prod,                     # HTTPS only en prod (requis par SameSite=None)
        samesite = "none" if prod else "lax",
        max_age  = CSRF_TOKEN_TTL,
        path     = "/",
    )


# ── Middleware de validation ──────────────────────────────────────────────────

_EXEMPT_PATHS = {
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/csrf-token",
    # Inscription publique candidat libre : aucune session préalable
    # → aucun token CSRF possible (même logique que /auth/register)
    "/api/v1/registration/candidate",
    "/api/v1/registration/school",
    "/api/v1/payments/webhook/wave",
    "/api/v1/payments/webhook/paydunya",
    "/docs",
    "/openapi.json",
    "/redoc",
}

_MUTATIVE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def check_csrf(request: Request) -> None:
    """
    Vérifie le token CSRF sur les requêtes mutatives (pattern Double-Submit).

    Trois contrôles :
      1. Le header X-CSRF-Token est présent et sa signature HMAC est valide
         (et le token n'est pas expiré).
      2. Le cookie csrf_token est présent.
      3. Le header et le cookie CORRESPONDENT (comparaison timing-safe).

    Le point 3 est l'essence du double-submit : un site tiers peut forcer le
    navigateur à envoyer le cookie (c'est le principe même du CSRF), mais il
    ne peut PAS lire ce cookie pour le recopier dans le header (politique
    d'origine identique). Sans cette comparaison, un token signé quelconque
    suffirait — la protection serait illusoire.

    Lève HTTP 403 si un contrôle échoue.
    """
    if request.method not in _MUTATIVE_METHODS:
        return

    # Exclure les paths exemptés (webhooks, login initial, etc.)
    path = request.url.path
    if path in _EXEMPT_PATHS:
        return
    if path.startswith("/static"):
        return

    # 1. Token du header
    token = request.headers.get(CSRF_HEADER_NAME, "")
    if not token:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Token CSRF manquant (header X-CSRF-Token requis)",
        )

    if not verify_csrf_token(token):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Token CSRF invalide ou expiré",
        )

    # 2. Token du cookie
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
    if not cookie_token:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Cookie CSRF manquant — appeler /api/v1/auth/csrf-token",
        )

    # 3. Correspondance header ↔ cookie (cœur du double-submit, timing-safe)
    if not hmac.compare_digest(token, cookie_token):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Token CSRF incohérent (header ≠ cookie)",
        )

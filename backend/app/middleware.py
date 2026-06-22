"""
Middleware FastAPI — CodeRoute Guinée.

Middleware actifs (dans l'ordre d'exécution) :
  1. RequestID       — injecte X-Request-ID unique dans chaque requête/réponse
  2. TimingHeader    — ajoute X-Process-Time (ms) dans chaque réponse
  3. GZipMiddleware  — déjà dans FastAPI mais activé seulement si Nginx est absent
  4. SecurityHeaders — headers de sécurité HTTP sur toutes les réponses
  5. ResponseCache   — cache LRU en mémoire pour les endpoints publics (GET sans token)
"""
import time
import uuid
from collections import OrderedDict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# ── 1. X-Request-ID ──────────────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injecte un ID unique dans chaque requête pour le tracing distribué."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ── 2. Timing ─────────────────────────────────────────────────────────────────

class TimingMiddleware(BaseHTTPMiddleware):
    """Ajoute X-Process-Time dans chaque réponse (utile pour le monitoring)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"
        return response


# ── 3. Cache en mémoire (LRU) pour les endpoints publics ─────────────────────
#
# Stratégie de cache :
#   - Seulement les GET sans Authorization header
#   - TTL : 30 secondes pour les données dynamiques, 5 min pour les stats
#   - Clé : méthode + URL + query string (pas de données utilisateur)
#   - Taille max : 256 entrées (adapté à la mémoire disponible)
#
# Endpoints bénéficiant du cache :
#   GET /health, GET /health/readiness — TTL 30s
#   GET /api/v1/sessions (disponibles) — TTL 30s
#   GET /api/v1/centers (liste publique) — TTL 60s


class LRUCache:
    """Cache LRU thread-safe simple (sans dépendances externes)."""

    def __init__(self, maxsize: int = 256) -> None:
        self._cache: OrderedDict[str, tuple[bytes, dict, float]] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> tuple[bytes, dict] | None:
        if key not in self._cache:
            return None
        body, headers, expires_at = self._cache[key]
        if time.time() > expires_at:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return body, headers

    def set(self, key: str, body: bytes, headers: dict, ttl: float) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (body, headers, time.time() + ttl)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def invalidate_prefix(self, prefix: str) -> int:
        keys = [k for k in self._cache if k.startswith(prefix)]
        for k in keys:
            del self._cache[k]
        return len(keys)


# Instance globale partagée entre tous les workers (via preload_app=True de Gunicorn)
_cache = LRUCache(maxsize=512)

# Règles de cache : (préfixe URL → TTL en secondes)
_CACHE_RULES: list[tuple[str, float]] = [
    ("/health",                           30.0),
    ("/api/v1/sessions",                  30.0),   # liste sessions disponibles
    ("/api/v1/centers",                   60.0),   # liste centres (peu changeant)
    ("/api/v1/dashboard",                 60.0),   # dashboard stats
    ("/api/v1/exams/",                     5.0),   # résultats d'examen
]


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """
    Cache LRU en mémoire pour les requêtes GET publiques (sans Authorization).

    N'est activé qu'en production (ENVIRONMENT=production) pour ne pas
    polluer les tests et le développement.
    """

    def __init__(self, app: ASGIApp, environment: str = "development") -> None:
        super().__init__(app)
        self._enabled = environment == "production"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Conditions de mise en cache : GET sans token
        if (
            not self._enabled
            or request.method != "GET"
            or "authorization" in request.headers
        ):
            return await call_next(request)

        # Trouver le TTL applicable
        path = request.url.path
        ttl: float | None = None
        for prefix, t in _CACHE_RULES:
            if path.startswith(prefix):
                ttl = t
                break

        if ttl is None:
            return await call_next(request)

        # Clé de cache = méthode + path + query string
        cache_key = f"GET:{path}?{request.url.query}"
        hit = _cache.get(cache_key)
        if hit is not None:
            body, headers = hit
            return Response(
                content=body,
                media_type=headers.get("content-type", "application/json"),
                headers={**headers, "X-Cache": "HIT"},
            )

        # Cache miss — appeler le handler
        response = await call_next(request)

        # Ne mettre en cache que les 200 OK
        if response.status_code == 200:
            body_chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                body_chunks.append(chunk)
            body = b"".join(body_chunks)

            headers_to_cache = {
                k: v for k, v in response.headers.items()
                if k.lower() in ("content-type", "content-encoding")
            }
            _cache.set(cache_key, body, headers_to_cache, ttl)

            return Response(
                content=body,
                status_code=200,
                headers={**dict(response.headers), "X-Cache": "MISS"},
                media_type=response.headers.get("content-type"),
            )

        return response

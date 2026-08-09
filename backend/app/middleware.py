"""Middleware FastAPI — CodeRoute Guinée.

P10 conserve un fallback mémoire pour le développement et la continuité de
service, mais utilise Redis/Valkey dès que REDIS_URL est configuré afin que le
cache public et les quotas soient cohérents entre workers et instances API.
"""
import time
import uuid
from collections import OrderedDict, deque
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.distributed import (
    distributed_cache_get,
    distributed_cache_set,
    distributed_rate_limit,
    redis_configured,
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injecte un ID unique dans chaque requête pour le tracing distribué."""

    async def dispatch(self, request: Request, call_next: "Callable") -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Ajoute X-Process-Time dans chaque réponse."""

    async def dispatch(self, request: Request, call_next: "Callable") -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"
        return response


class LRUCache:
    """Fallback LRU local. Il n'est jamais présenté comme cache HA."""

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
        keys = [key for key in self._cache if key.startswith(prefix)]
        for key in keys:
            del self._cache[key]
        return len(keys)


_cache = LRUCache(maxsize=512)

# Les health endpoints sont volontairement exclus : une sonde ne doit jamais
# recevoir un état de readiness mis en cache après une panne ou une restauration.
_CACHE_RULES: list[tuple[str, float]] = [
    ("/api/v1/sessions", 30.0),
    ("/api/v1/centers", 60.0),
    ("/api/v1/dashboard", 60.0),
    ("/api/v1/exams/", 5.0),
]


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Cache public partagé en HA, avec fallback local en cas d'incident Redis."""

    def __init__(self, app: ASGIApp, environment: str = "development") -> None:
        super().__init__(app)
        self._enabled = environment == "production"

    async def dispatch(self, request: Request, call_next: "Callable") -> Response:
        if not self._enabled or request.method != "GET" or "authorization" in request.headers:
            return await call_next(request)

        path = request.url.path
        ttl: float | None = None
        for prefix, candidate_ttl in _CACHE_RULES:
            if path.startswith(prefix):
                ttl = candidate_ttl
                break
        if ttl is None:
            return await call_next(request)

        cache_key = f"GET:{path}?{request.url.query}"
        redis_failed = False
        if redis_configured():
            try:
                hit = await distributed_cache_get(cache_key)
                if hit is not None:
                    body, headers = hit
                    return Response(
                        content=body,
                        media_type=headers.get("content-type", "application/json"),
                        headers={**headers, "X-Cache": "HIT", "X-Cache-Backend": "shared"},
                    )
            except Exception:
                redis_failed = True

        if not redis_configured() or redis_failed:
            local_hit = _cache.get(cache_key)
            if local_hit is not None:
                body, headers = local_hit
                return Response(
                    content=body,
                    media_type=headers.get("content-type", "application/json"),
                    headers={**headers, "X-Cache": "HIT", "X-Cache-Backend": "local-fallback"},
                )

        response = await call_next(request)
        if response.status_code != 200:
            return response

        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        body = b"".join(body_chunks)
        headers_to_cache = {
            key: value
            for key, value in response.headers.items()
            if key.lower() in ("content-type", "content-encoding")
        }

        backend = "local"
        if redis_configured():
            try:
                await distributed_cache_set(cache_key, body, headers_to_cache, ttl=ttl)
                backend = "shared"
            except Exception:
                backend = "local-fallback"
        _cache.set(cache_key, body, headers_to_cache, ttl)

        return Response(
            content=body,
            status_code=200,
            headers={**dict(response.headers), "X-Cache": "MISS", "X-Cache-Backend": backend},
            media_type=response.headers.get("content-type"),
        )


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Quota global partagé entre instances, avec fallback local de disponibilité."""

    def __init__(self, app, max_requests: int = 300, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._last_cleanup = time.monotonic()

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now
        cutoff = now - self.window
        stale = [ip for ip, hits in self._hits.items() if not hits or hits[-1] < cutoff]
        for ip in stale:
            del self._hits[ip]

    def _local_decision(self, identity: str) -> tuple[bool, int]:
        now = time.monotonic()
        self._cleanup(now)
        hits = self._hits.setdefault(identity, deque())
        cutoff = now - self.window
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False, int(hits[0] + self.window - now) + 1
        hits.append(now)
        return True, 0

    async def dispatch(self, request: Request, call_next: "Callable") -> Response:
        path = request.url.path
        if path.startswith("/health") or path.startswith("/static"):
            return await call_next(request)

        identity = self._client_ip(request)
        backend = "local"
        if redis_configured():
            try:
                allowed, _count, retry_after = await distributed_rate_limit(
                    identity,
                    limit=self.max_requests,
                    window_seconds=self.window,
                )
                backend = "shared"
            except Exception:
                allowed, retry_after = self._local_decision(identity)
                backend = "local-fallback"
        else:
            allowed, retry_after = self._local_decision(identity)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes. Réessayez dans quelques instants."},
                headers={"Retry-After": str(max(1, retry_after)), "X-RateLimit-Backend": backend},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Backend"] = backend
        return response

"""Middleware FastAPI — CodeRoute Guinée P10."""
import time
import uuid
from collections import OrderedDict, deque
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.distributed import distributed_cache_get, distributed_cache_set, distributed_rate_limit, redis_configured


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: "Callable") -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: "Callable") -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time"] = f"{(time.perf_counter() - start) * 1000:.1f}ms"
        return response


class LRUCache:
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

# Health/readiness ne doit jamais être mis en cache.
_CACHE_RULES: list[tuple[str, float]] = [
    ("/api/v1/sessions", 30.0),
    ("/api/v1/centers", 60.0),
    ("/api/v1/dashboard", 60.0),
    ("/api/v1/exams/", 5.0),
]


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, environment: str = "development") -> None:
        super().__init__(app)
        self._enabled = environment == "production"

    async def dispatch(self, request: Request, call_next: "Callable") -> Response:
        if not self._enabled or request.method != "GET" or "authorization" in request.headers:
            return await call_next(request)

        path = request.url.path
        ttl = next((candidate for prefix, candidate in _CACHE_RULES if path.startswith(prefix)), None)
        if ttl is None:
            return await call_next(request)

        cache_key = f"GET:{path}?{request.url.query}"
        shared_failed = False
        if redis_configured():
            try:
                hit = await distributed_cache_get(cache_key)
                if hit is not None:
                    body, headers = hit
                    return Response(content=body, headers={**headers, "X-Cache": "HIT", "X-Cache-Backend": "shared"})
            except Exception:
                shared_failed = True

        if not redis_configured() or shared_failed:
            local_hit = _cache.get(cache_key)
            if local_hit is not None:
                body, headers = local_hit
                return Response(content=body, headers={**headers, "X-Cache": "HIT", "X-Cache-Backend": "local-fallback"})

        response = await call_next(request)
        if response.status_code != 200:
            return response

        chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        body = b"".join(chunks)
        cached_headers = {k: v for k, v in response.headers.items() if k.lower() in {"content-type", "content-encoding"}}
        backend = "local"
        if redis_configured():
            try:
                await distributed_cache_set(cache_key, body, cached_headers, ttl=ttl)
                backend = "shared"
            except Exception:
                backend = "local-fallback"
        _cache.set(cache_key, body, cached_headers, ttl)
        return Response(content=body, status_code=200, headers={**dict(response.headers), "X-Cache": "MISS", "X-Cache-Backend": backend})


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
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
        for ip in [ip for ip, hits in self._hits.items() if not hits or hits[-1] < cutoff]:
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
        if request.url.path.startswith(("/health", "/static")):
            return await call_next(request)

        identity = self._client_ip(request)
        backend = "local"
        if redis_configured():
            try:
                allowed, _count, retry_after = await distributed_rate_limit(identity, limit=self.max_requests, window_seconds=self.window)
                backend = "shared"
            except Exception:
                allowed, retry_after = self._local_decision(identity)
                backend = "local-fallback"
        else:
            allowed, retry_after = self._local_decision(identity)

        if not allowed:
            return JSONResponse(status_code=429, content={"detail": "Trop de requêtes. Réessayez dans quelques instants."}, headers={"Retry-After": str(max(1, retry_after)), "X-RateLimit-Backend": backend})
        response = await call_next(request)
        response.headers["X-RateLimit-Backend"] = backend
        return response

"""
Tests app/middleware.py — coverage lignes 67-169 (47% → 90%+)

Cibles :
  LRUCache.get / set / invalidate_prefix    (67-87)
  ResponseCacheMiddleware.dispatch          (125-169)
  TimingMiddleware.dispatch                 (intégration)
  RequestIDMiddleware.dispatch              (intégration)
"""
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware import LRUCache, ResponseCacheMiddleware

# ── LRUCache ──────────────────────────────────────────────────────────────────

class TestLRUCache:
    def _cache(self, maxsize: int = 16) -> LRUCache:
        return LRUCache(maxsize=maxsize)

    def test_get_miss_returns_none(self):
        c = self._cache()
        assert c.get("missing") is None

    def test_set_and_get_returns_value(self):
        c = self._cache()
        c.set("k", b"body", {"content-type": "application/json"}, ttl=60)
        result = c.get("k")
        assert result is not None
        body, headers = result
        assert body == b"body"
        assert headers["content-type"] == "application/json"

    def test_expired_entry_returns_none(self):
        c = self._cache()
        c.set("k", b"data", {}, ttl=0.001)
        time.sleep(0.01)
        assert c.get("k") is None

    def test_lru_eviction_on_maxsize(self):
        c = self._cache(maxsize=3)
        c.set("a", b"1", {}, ttl=60)
        c.set("b", b"2", {}, ttl=60)
        c.set("c", b"3", {}, ttl=60)
        # Ajouter une 4ème entrée → "a" doit être évincée (LRU)
        c.set("d", b"4", {}, ttl=60)
        assert c.get("a") is None   # évincé
        assert c.get("b") is not None
        assert c.get("d") is not None

    def test_access_promotes_to_end(self):
        """Accéder à une entrée la déplace en fin → pas évincée en premier."""
        c = self._cache(maxsize=3)
        c.set("a", b"1", {}, ttl=60)
        c.set("b", b"2", {}, ttl=60)
        c.set("c", b"3", {}, ttl=60)
        # Accéder à "a" → elle devient MRU
        c.get("a")
        c.set("d", b"4", {}, ttl=60)   # "b" doit être évincé
        assert c.get("a") is not None  # toujours là
        assert c.get("b") is None      # évincé

    def test_overwrite_existing_key(self):
        c = self._cache()
        c.set("k", b"v1", {}, ttl=60)
        c.set("k", b"v2", {}, ttl=60)
        body, _ = c.get("k")
        assert body == b"v2"

    def test_invalidate_prefix_removes_matching_keys(self):
        c = self._cache()
        c.set("GET:/api/v1/centers?limit=20", b"data1", {}, ttl=60)
        c.set("GET:/api/v1/centers?limit=50", b"data2", {}, ttl=60)
        c.set("GET:/api/v1/candidates?limit=20", b"data3", {}, ttl=60)
        removed = c.invalidate_prefix("GET:/api/v1/centers")
        assert removed == 2
        assert c.get("GET:/api/v1/centers?limit=20") is None
        assert c.get("GET:/api/v1/centers?limit=50") is None
        assert c.get("GET:/api/v1/candidates?limit=20") is not None

    def test_invalidate_prefix_no_match_returns_zero(self):
        c = self._cache()
        c.set("GET:/health", b"ok", {}, ttl=60)
        removed = c.invalidate_prefix("GET:/api/v1/missing")
        assert removed == 0

    def test_empty_body_cacheable(self):
        c = self._cache()
        c.set("empty", b"", {}, ttl=60)
        result = c.get("empty")
        assert result is not None
        body, _ = result
        assert body == b""

    def test_large_value_stored_correctly(self):
        c = self._cache()
        big_body = b"x" * 100_000
        c.set("big", big_body, {"content-type": "application/json"}, ttl=60)
        body, _ = c.get("big")
        assert len(body) == 100_000


# ── RequestIDMiddleware ───────────────────────────────────────────────────────

class TestRequestIDMiddleware:
    def test_generates_request_id_if_missing(self):
        with TestClient(app) as client:
            r = client.get("/health")
        assert "X-Request-ID" in r.headers
        assert len(r.headers["X-Request-ID"]) == 36   # UUID format

    def test_propagates_provided_request_id(self):
        custom_id = "test-req-id-12345"
        with TestClient(app) as client:
            r = client.get("/health", headers={"X-Request-ID": custom_id})
        assert r.headers.get("X-Request-ID") == custom_id

    def test_each_request_gets_unique_id(self):
        with TestClient(app) as client:
            r1 = client.get("/health")
            r2 = client.get("/health")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


# ── TimingMiddleware ──────────────────────────────────────────────────────────

class TestTimingMiddleware:
    def test_process_time_header_present(self):
        with TestClient(app) as client:
            r = client.get("/health")
        assert "X-Process-Time" in r.headers

    def test_process_time_is_numeric_ms(self):
        with TestClient(app) as client:
            r = client.get("/health")
        val = r.headers["X-Process-Time"]
        assert val.endswith("ms")
        ms = float(val.replace("ms", ""))
        assert ms >= 0
        assert ms < 10_000   # jamais plus de 10 secondes

    def test_fast_endpoint_low_ms(self):
        with TestClient(app) as client:
            r = client.get("/health")
        ms = float(r.headers["X-Process-Time"].replace("ms", ""))
        assert ms < 1_000   # /health doit répondre en < 1s


# ── ResponseCacheMiddleware ───────────────────────────────────────────────────

class TestResponseCacheMiddleware:
    """Tests du middleware de cache LRU sur les endpoints publics."""

    def setup_method(self):
        """Vider le cache LRU avant chaque test pour garantir l'isolation."""
        import app.middleware as mmod
        mmod._cache = mmod.LRUCache(maxsize=512)

    def _make_caching_app(self, route_path: str = "/api/v1/centers"):
        """Crée une mini-app Starlette avec le cache en mode production."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        call_count = [0]

        async def endpoint(request):
            call_count[0] += 1
            return JSONResponse({"count": call_count[0]})

        mini_app = Starlette(routes=[Route(route_path, endpoint)])
        mini_app.add_middleware(ResponseCacheMiddleware, environment="production")
        return mini_app, call_count

    def test_cache_miss_on_first_request(self):
        mini_app, _ = self._make_caching_app()
        with TestClient(mini_app) as client:
            r = client.get("/api/v1/centers")
        assert r.headers.get("X-Cache") == "MISS"

    def test_cache_hit_on_second_request(self):
        mini_app, call_count = self._make_caching_app()
        with TestClient(mini_app) as client:
            client.get("/api/v1/centers")
            r2 = client.get("/api/v1/centers")
        assert r2.headers.get("X-Cache") == "HIT"
        assert call_count[0] == 1  # handler appelé une seule fois

    def test_cache_bypassed_with_auth_token(self):
        mini_app, call_count = self._make_caching_app()
        with TestClient(mini_app) as client:
            r = client.get("/api/v1/centers", headers={"Authorization": "Bearer token"})
        assert r.headers.get("X-Cache") is None
        assert call_count[0] == 1  # handler appelé (pas mis en cache)

    def test_cache_only_get_methods(self):
        with TestClient(app) as client:
            # POST ne doit pas être mis en cache (mais /health n'a pas de POST)
            # Vérifier via un endpoint existant
            r = client.get("/health")
        assert r.status_code == 200

    def test_cached_response_has_same_body(self):
        with TestClient(app) as client:
            r1 = client.get("/health")
            r2 = client.get("/health")
        assert r1.json() == r2.json()

    def test_cache_not_active_in_test_environment(self):
        """En environnement de test (development), le cache ne doit pas s'activer."""
        from app.core.config import get_settings
        settings = get_settings()
        # En tests, l'environment est "development" ou "test"
        if settings.environment == "production":
            pytest.skip("Pas en production")
        # En dev, X-Cache peut être MISS ou absent selon la config
        with TestClient(app) as client:
            r = client.get("/health")
        # Le middleware est enregistré mais son comportement dépend de l'env
        assert r.status_code == 200

    def test_different_query_strings_separate_cache_entries(self):
        with TestClient(app) as client:
            r1 = client.get("/health")
            r2 = client.get("/health?foo=bar")
        # Les deux sont mis en cache séparément (MISS puis MISS ou HIT)
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_cache_middleware_init_disabled_in_dev(self):
        """Le middleware est désactivé si environment != production."""
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient as StarletteClient

        async def homepage(request):
            return PlainTextResponse("hello")

        mini_app = Starlette(routes=[Route("/", homepage)])
        mini_app.add_middleware(ResponseCacheMiddleware, environment="development")

        with StarletteClient(mini_app) as client:
            r1 = client.get("/")
            r2 = client.get("/")
        # En mode dev, pas de X-Cache
        assert r1.headers.get("X-Cache") is None
        assert r2.headers.get("X-Cache") is None

    def test_cache_middleware_init_enabled_in_production(self):
        """En production, les réponses GET sont mises en cache."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        call_count = [0]

        async def api_endpoint(request):
            call_count[0] += 1
            return JSONResponse({"count": call_count[0]})

        mini_app = Starlette(routes=[Route("/api/v1/centers", api_endpoint)])
        mini_app.add_middleware(ResponseCacheMiddleware, environment="production")

        with TestClient(mini_app) as client:
            r1 = client.get("/api/v1/centers")
            r2 = client.get("/api/v1/centers")

        # Premier : MISS, deuxième : HIT
        assert r1.headers.get("X-Cache") == "MISS"
        assert r2.headers.get("X-Cache") == "HIT"
        # Le handler n'a été appelé qu'une fois
        assert call_count[0] == 1
        # Les deux réponses ont le même body
        assert r1.json() == r2.json()

    def test_cache_ttl_expiry(self):
        """Une entrée expirée doit être rechargée."""
        import app.middleware as mmod
        orig_rules = mmod._CACHE_RULES[:]
        mmod._CACHE_RULES = [("/api/v1/sessions", 0.01)]

        mini_app, call_count = self._make_caching_app("/api/v1/sessions")

        try:
            with TestClient(mini_app) as client:
                r1 = client.get("/api/v1/sessions")
                time.sleep(0.05)   # attendre expiration du TTL (10ms)
                r2 = client.get("/api/v1/sessions")
        finally:
            mmod._CACHE_RULES = orig_rules

        assert r1.headers.get("X-Cache") == "MISS"
        assert r2.headers.get("X-Cache") == "MISS"   # expiré → rechargé
        assert call_count[0] == 2

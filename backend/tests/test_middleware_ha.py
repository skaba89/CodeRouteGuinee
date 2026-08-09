from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import middleware as middleware_module
from app.middleware import GlobalRateLimitMiddleware, ResponseCacheMiddleware


def test_public_cache_hit_uses_shared_backend(monkeypatch) -> None:
    app = FastAPI()
    calls = {"handler": 0}

    @app.get("/api/v1/centers")
    async def centers():
        calls["handler"] += 1
        return {"source": "handler"}

    async def fake_get(_key: str):
        return b'{"source":"shared"}', {"content-type": "application/json"}

    monkeypatch.setattr(middleware_module, "redis_configured", lambda: True)
    monkeypatch.setattr(middleware_module, "distributed_cache_get", fake_get)
    app.add_middleware(ResponseCacheMiddleware, environment="production")

    response = TestClient(app).get("/api/v1/centers")
    assert response.status_code == 200
    assert response.json() == {"source": "shared"}
    assert response.headers["X-Cache"] == "HIT"
    assert response.headers["X-Cache-Backend"] == "shared"
    assert calls["handler"] == 0


def test_global_rate_limit_rejection_is_shared_across_instances(monkeypatch) -> None:
    app = FastAPI()

    @app.get("/api/test")
    async def endpoint():
        return {"ok": True}

    async def reject(_identity: str, *, limit: int, window_seconds: int):
        assert limit == 300
        assert window_seconds == 60
        return False, 300, 7

    monkeypatch.setattr(middleware_module, "redis_configured", lambda: True)
    monkeypatch.setattr(middleware_module, "distributed_rate_limit", reject)
    app.add_middleware(GlobalRateLimitMiddleware)

    response = TestClient(app).get("/api/test", headers={"x-forwarded-for": "203.0.113.8"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "7"
    assert response.headers["X-RateLimit-Backend"] == "shared"


def test_global_rate_limit_falls_back_locally_when_shared_state_errors(monkeypatch) -> None:
    app = FastAPI()

    @app.get("/api/test")
    async def endpoint():
        return {"ok": True}

    async def fail_shared(*_args, **_kwargs):
        raise RuntimeError("shared state unavailable")

    monkeypatch.setattr(middleware_module, "redis_configured", lambda: True)
    monkeypatch.setattr(middleware_module, "distributed_rate_limit", fail_shared)
    app.add_middleware(GlobalRateLimitMiddleware, max_requests=2, window_seconds=60)

    client = TestClient(app)
    first = client.get("/api/test", headers={"x-forwarded-for": "203.0.113.9"})
    second = client.get("/api/test", headers={"x-forwarded-for": "203.0.113.9"})
    third = client.get("/api/test", headers={"x-forwarded-for": "203.0.113.9"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers["X-RateLimit-Backend"] == "local-fallback"
    assert third.status_code == 429
    assert third.headers["X-RateLimit-Backend"] == "local-fallback"

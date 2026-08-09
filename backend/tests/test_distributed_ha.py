from __future__ import annotations

import asyncio
import json

import pytest

from app import distributed


class FakeAsyncRedis:
    def __init__(self):
        self.values = {}
        self.eval_result = [1, 1, 0]
        self.eval_calls = []

    async def eval(self, *args):
        self.eval_calls.append(args)
        return self.eval_result

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex):
        assert ex >= 1
        self.values[key] = value
        return True


class BrokenSyncRedis:
    def ping(self):
        raise ConnectionError("redis unavailable")


def test_distributed_rate_limit_accepts_and_rejects_from_shared_backend(monkeypatch):
    fake = FakeAsyncRedis()
    monkeypatch.setattr(distributed, "get_async_redis", lambda: fake)
    monkeypatch.setattr(distributed, "cache_namespace", lambda: "coderoute:test")
    allowed, count, retry = asyncio.run(distributed.distributed_rate_limit("203.0.113.4", limit=3, window_seconds=60))
    assert allowed is True and count == 1 and retry == 0 and fake.eval_calls
    fake.eval_result = [0, 3, 2500]
    allowed, count, retry = asyncio.run(distributed.distributed_rate_limit("203.0.113.4", limit=3, window_seconds=60))
    assert allowed is False and count == 3 and retry == 3


def test_distributed_cache_round_trip_is_binary_safe(monkeypatch):
    fake = FakeAsyncRedis()
    monkeypatch.setattr(distributed, "get_async_redis", lambda: fake)
    monkeypatch.setattr(distributed, "cache_namespace", lambda: "coderoute:test")
    body = b"\x00CodeRoute\xff"
    headers = {"content-type": "application/octet-stream"}
    asyncio.run(distributed.distributed_cache_set("GET:/public?", body, headers, ttl=15))
    restored = asyncio.run(distributed.distributed_cache_get("GET:/public?"))
    assert restored is not None
    assert restored[0] == body and restored[1] == headers
    stored_json = next(iter(fake.values.values()))
    assert "CodeRoute" not in stored_json
    assert json.loads(stored_json)["body_b64"]


def test_shared_state_outage_is_degraded_when_reconstructible(monkeypatch):
    monkeypatch.setattr(distributed, "redis_configured", lambda: True)
    monkeypatch.setattr(distributed, "redis_is_required", lambda: False)
    monkeypatch.setattr(distributed, "get_sync_redis", lambda: BrokenSyncRedis())
    check = distributed.check_shared_state()
    assert check["status"] == "degraded"
    assert check["required"] is False
    assert check["detail"] == "ConnectionError"


def test_shared_state_outage_is_blocking_only_in_explicit_strict_mode(monkeypatch):
    monkeypatch.setattr(distributed, "redis_configured", lambda: True)
    monkeypatch.setattr(distributed, "redis_is_required", lambda: True)
    monkeypatch.setattr(distributed, "get_sync_redis", lambda: BrokenSyncRedis())
    check = distributed.check_shared_state()
    assert check["status"] == "error"
    assert check["required"] is True


def test_distributed_helpers_fail_closed_when_no_client(monkeypatch):
    monkeypatch.setattr(distributed, "get_async_redis", lambda: None)
    with pytest.raises(RuntimeError, match="shared state"):
        asyncio.run(distributed.distributed_rate_limit("ip", limit=1, window_seconds=1))
    with pytest.raises(RuntimeError, match="shared state"):
        asyncio.run(distributed.distributed_cache_get("key"))

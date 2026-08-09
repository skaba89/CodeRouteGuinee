"""État partagé multi-instance pour CodeRoute Guinée.

P10 utilise un datastore Redis-compatible (Redis ou Valkey) uniquement pour des
informations tolérantes à la perte : cache HTTP public et rate limiting. Les
données d'examen restent dans PostgreSQL / Center Edge et ne dépendent jamais
de ce cache pour leur intégrité.
"""
from __future__ import annotations

import base64
import json
import os
import time
import uuid
from functools import lru_cache
from typing import Any

import redis
import redis.asyncio as aioredis

from app.core.config import get_settings


_RATE_LIMIT_LUA = """
local key = KEYS[1]
local cutoff = tonumber(ARGV[1])
local now_ms = tonumber(ARGV[2])
local window_ms = tonumber(ARGV[3])
local limit = tonumber(ARGV[4])
local member = ARGV[5]
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry_ms = window_ms
  if oldest[2] then
    retry_ms = math.max(1, tonumber(oldest[2]) + window_ms - now_ms)
  end
  return {0, count, retry_ms}
end
redis.call('ZADD', key, now_ms, member)
redis.call('PEXPIRE', key, window_ms)
return {1, count + 1, 0}
"""


def _settings():
    return get_settings()


def redis_url() -> str:
    return str(getattr(_settings(), "redis_url", "") or "").strip()


def redis_configured() -> bool:
    return bool(redis_url())


def redis_is_required() -> bool:
    settings = _settings()
    return bool(getattr(settings, "redis_required", False) or getattr(settings, "ha_mode", False))


def cache_namespace() -> str:
    settings = _settings()
    environment = str(getattr(settings, "environment", "development") or "development").strip().lower()
    deployment = str(getattr(settings, "deployment_id", "") or "").strip()
    suffix = deployment or environment
    return f"coderoute:{suffix}"


def instance_id() -> str:
    configured = str(getattr(_settings(), "instance_id", "") or "").strip()
    return configured or os.environ.get("RENDER_INSTANCE_ID") or os.environ.get("HOSTNAME") or "unknown"


@lru_cache(maxsize=1)
def get_sync_redis():
    url = redis_url()
    if not url:
        return None
    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )


@lru_cache(maxsize=1)
def get_async_redis():
    url = redis_url()
    if not url:
        return None
    return aioredis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )


def check_shared_state() -> dict[str, Any]:
    """Probe synchrone sans exposer l'URL ou les credentials."""
    if not redis_configured():
        return {
            "status": "error" if redis_is_required() else "disabled",
            "required": redis_is_required(),
            "backend": "redis-compatible",
        }
    client = get_sync_redis()
    started = time.perf_counter()
    try:
        assert client is not None
        client.ping()
        return {
            "status": "ok",
            "required": redis_is_required(),
            "backend": "redis-compatible",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    except Exception as exc:
        return {
            "status": "error",
            "required": redis_is_required(),
            "backend": "redis-compatible",
            "detail": exc.__class__.__name__,
        }


async def distributed_rate_limit(identity: str, *, limit: int, window_seconds: int) -> tuple[bool, int, int]:
    """Sliding window atomique partagée par tous les workers/instances."""
    client = get_async_redis()
    if client is None:
        raise RuntimeError("shared state not configured")
    now_ms = int(time.time() * 1000)
    window_ms = max(1, int(window_seconds * 1000))
    key = f"{cache_namespace()}:ratelimit:{identity}"
    member = f"{now_ms}:{uuid.uuid4().hex}"
    result = await client.eval(
        _RATE_LIMIT_LUA,
        1,
        key,
        now_ms - window_ms,
        now_ms,
        window_ms,
        max(1, limit),
        member,
    )
    allowed = bool(int(result[0]))
    count = int(result[1])
    retry_ms = int(result[2])
    retry_after = max(1, (retry_ms + 999) // 1000) if not allowed else 0
    return allowed, count, retry_after


async def distributed_cache_get(key: str) -> tuple[bytes, dict[str, str]] | None:
    client = get_async_redis()
    if client is None:
        raise RuntimeError("shared state not configured")
    raw = await client.get(f"{cache_namespace()}:httpcache:{key}")
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        body = base64.b64decode(payload["body_b64"], validate=True)
        headers = payload.get("headers") or {}
        if not isinstance(headers, dict):
            return None
        return body, {str(k): str(v) for k, v in headers.items()}
    except Exception:
        return None


async def distributed_cache_set(key: str, body: bytes, headers: dict[str, str], *, ttl: float) -> None:
    client = get_async_redis()
    if client is None:
        raise RuntimeError("shared state not configured")
    payload = {
        "body_b64": base64.b64encode(body).decode("ascii"),
        "headers": headers,
    }
    await client.set(
        f"{cache_namespace()}:httpcache:{key}",
        json.dumps(payload, separators=(",", ":")),
        ex=max(1, int(ttl)),
    )

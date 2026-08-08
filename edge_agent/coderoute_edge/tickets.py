from __future__ import annotations

import hashlib
import hmac
import time


def media_ticket(storage_key: bytes, attempt_id: str, digest: str, expires_at: int) -> str:
    message = f"coderoute-edge-media-v1\x00{attempt_id}\x00{digest}\x00{int(expires_at)}".encode("utf-8")
    return hmac.new(storage_key, message, hashlib.sha256).hexdigest()


def verify_media_ticket(
    storage_key: bytes,
    attempt_id: str,
    digest: str,
    expires_at: int,
    ticket: str,
    *,
    now: int | None = None,
) -> bool:
    reference = int(time.time()) if now is None else int(now)
    if int(expires_at) < reference:
        return False
    expected = media_ticket(storage_key, attempt_id, digest, int(expires_at))
    return hmac.compare_digest(expected, ticket or "")

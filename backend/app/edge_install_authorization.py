from __future__ import annotations

import base64
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from app.edge_offline import canonical_json, sha256_hex
from app.edge_release import release_signing_key_id, release_signing_private_key

EDGE_INSTALL_AUTHORIZATION_KIND = "center_edge_install_authorization_v1"
EDGE_INSTALL_AUTHORIZATION_TTL_SECONDS = max(
    300,
    min(3600, int(os.environ.get("CODEROUTE_EDGE_INSTALL_AUTH_TTL_SECONDS", "1200"))),
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _iso(value: datetime) -> str:
    aware = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def sign_install_authorization(
    *,
    release_id: str,
    source_release_id: str | None,
    node_id: str,
    center_id: str,
    action: str,
    current_version: str,
    software_version: str,
    artifact_sha256: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    issued = now or datetime.now(UTC)
    expires = issued + timedelta(seconds=EDGE_INSTALL_AUTHORIZATION_TTL_SECONDS)
    payload = {
        "kind": EDGE_INSTALL_AUTHORIZATION_KIND,
        "version": 1,
        "release_id": release_id,
        "source_release_id": source_release_id,
        "node_id": node_id,
        "center_id": center_id,
        "action": action,
        "current_version": current_version.strip(),
        "software_version": software_version.strip(),
        "artifact_sha256": artifact_sha256.strip().lower(),
        "issued_at": _iso(issued),
        "expires_at": _iso(expires),
    }
    encoded = canonical_json(payload)
    signature = release_signing_private_key().sign(encoded)
    return {
        "payload": payload,
        "payload_hash": sha256_hex(encoded),
        "signature_b64": _b64url(signature),
        "signing_key_id": release_signing_key_id(),
    }

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .config import EdgeAgentConfig
from .crypto import sign_payload, verify_signed_payload
from .store import EdgeStore


def _iso_z(value: datetime) -> str:
    aware = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _machine_payload(
    *,
    action: str,
    node_id: str,
    center_id: str,
    sequence: int,
    sent_at: str,
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "action": action,
        "center_id": center_id,
        "node_id": node_id,
        "sent_at": sent_at,
        "sequence": int(sequence),
    }
    if fields:
        payload.update(fields)
    return payload


def _fleet_telemetry(value: dict[str, Any] | None) -> dict[str, int] | None:
    if value is None:
        return None

    def safe(key: str, maximum: int) -> int:
        try:
            parsed = int(value.get(key, 0) or 0)
        except (TypeError, ValueError):
            parsed = 0
        return min(max(parsed, 0), maximum)

    return {
        "active_leases": safe("active_leases", 100_000),
        "finalized_leases": safe("finalized_leases", 100_000),
        "synced_leases": safe("synced_leases", 10_000_000),
        "sync_pending": safe("sync_pending", 100_000),
        "revalidation_required": safe("revalidation_required", 100_000),
        "corrupt_leases": safe("corrupt_leases", 100_000),
        "media_files": safe("media_files", 1_000_000),
        "media_bytes": safe("media_bytes", 10_000_000_000_000),
    }


class CentralClient:
    def __init__(
        self,
        config: EdgeAgentConfig,
        store: EdgeStore,
        private_key: Ed25519PrivateKey,
        *,
        http: httpx.Client | None = None,
    ):
        self.config = config
        self.store = store
        self.private_key = private_key
        self.http = http or httpx.Client(
            base_url=config.central_url,
            timeout=30.0,
            follow_redirects=True,
        )
        self._owns_http = http is None
        self._csrf_token: str | None = None

    def close(self) -> None:
        if self._owns_http:
            self.http.close()

    def _ensure_csrf(self) -> str:
        if self._csrf_token:
            return self._csrf_token
        response = self.http.get("/api/v1/auth/csrf-token")
        response.raise_for_status()
        token = str(response.json()["csrf_token"])
        self._csrf_token = token
        return token

    def _post(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        token = self._ensure_csrf()
        response = self.http.post(path, json=payload, headers={"X-CSRF-Token": token})
        if response.status_code == 403 and "CSRF" in response.text.upper():
            self._csrf_token = None
            token = self._ensure_csrf()
            response = self.http.post(path, json=payload, headers={"X-CSRF-Token": token})
        response.raise_for_status()
        return response

    def heartbeat(self, telemetry: dict[str, Any] | None = None) -> dict[str, Any]:
        sequence = self.store.next_node_sequence()
        sent_at = datetime.now(UTC).replace(microsecond=0)
        capabilities = [
            "answer-journal-v1",
            "exam-lease-v1",
            "fleet-telemetry-v1",
            "media-prefetch-v1",
            "operator-status-v1",
        ]
        signing_payload: dict[str, Any] = {
            "capabilities": sorted(capabilities),
            "center_id": self.config.center_id,
            "node_id": self.config.node_id,
            "sent_at": _iso_z(sent_at),
            "sequence": sequence,
            "software_version": self.config.software_version,
        }
        normalized = _fleet_telemetry(telemetry)
        if normalized is not None:
            signing_payload["telemetry"] = normalized
        payload = {**signing_payload, "signature_b64": sign_payload(self.private_key, signing_payload)}
        return self._post("/api/v1/center-edge/heartbeat", payload).json()

    def issue_lease(self, attempt_id: str, lang: str = "fr") -> dict[str, Any]:
        sequence = self.store.next_node_sequence()
        sent_at = _iso_z(datetime.now(UTC))
        fields = {"attempt_id": attempt_id, "lang": lang.strip().lower()}
        signed = _machine_payload(
            action="lease.issue",
            node_id=self.config.node_id,
            center_id=self.config.center_id,
            sequence=sequence,
            sent_at=sent_at,
            fields=fields,
        )
        payload = {
            "node_id": self.config.node_id,
            "center_id": self.config.center_id,
            "sequence": sequence,
            "sent_at": sent_at,
            **fields,
            "signature_b64": sign_payload(self.private_key, signed),
        }
        return self._post("/api/v1/center-edge/leases/issue", payload).json()

    def lease_signing_key(self) -> dict[str, Any]:
        response = self.http.get("/api/v1/center-edge/lease-signing-key")
        response.raise_for_status()
        return response.json()

    def verify_lease_bundle(self, bundle: dict[str, Any]) -> bool:
        key = self.lease_signing_key()
        if str(bundle.get("signing_key_id")) != str(key.get("key_id")):
            return False
        return verify_signed_payload(
            str(key["public_key_b64"]),
            bundle["lease"],
            str(bundle["lease_signature_b64"]),
        )

    def sync_offline(self, sync_payload: dict[str, Any]) -> dict[str, Any]:
        sequence = self.store.next_node_sequence()
        sent_at = _iso_z(datetime.now(UTC))
        fields = {
            "lease_id": sync_payload["lease_id"],
            "finalized_elapsed_ms": int(sync_payload["finalized_elapsed_ms"]),
            "journal_head_hash": sync_payload["journal_head_hash"],
            "event_count": len(sync_payload["events"]),
        }
        signed = _machine_payload(
            action="lease.offline_sync",
            node_id=self.config.node_id,
            center_id=self.config.center_id,
            sequence=sequence,
            sent_at=sent_at,
            fields=fields,
        )
        payload = {
            "node_id": self.config.node_id,
            "center_id": self.config.center_id,
            "sequence": sequence,
            "sent_at": sent_at,
            **fields,
            "events": sync_payload["events"],
            "signature_b64": sign_payload(self.private_key, signed),
        }
        return self._post("/api/v1/center-edge/offline-sync", payload).json()

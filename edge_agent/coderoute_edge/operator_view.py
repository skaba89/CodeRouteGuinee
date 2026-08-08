from __future__ import annotations

import time
from typing import Any

from .media import MediaCache
from .store import EdgeStore


def _claim_state(row: Any, now: float) -> str:
    if row["claim_consumed_at"] is not None:
        return "claimed"
    expires_at = float(row["claim_expires_at"] or 0)
    if expires_at and expires_at < now:
        return "expired"
    if row["claim_token_hash"]:
        return "pending"
    return "unavailable"


def _safe_station(station: Any) -> dict[str, Any]:
    value = station if isinstance(station, dict) else {}
    return {
        "center_station_id": value.get("center_station_id"),
        "device_key": value.get("device_key"),
        "label": value.get("label"),
        "room": value.get("room"),
    }


def build_operator_status(store: EdgeStore, media: MediaCache) -> dict[str, Any]:
    """Construit une vue d'exploitation sans données d'examen sensibles.

    Cette fonction ne retourne jamais : questions/options, réponses candidat,
    token de claim, token d'accès, hash de poste, ciphertext ou journal brut.
    Un lease illisible reste visible comme incident local au lieu de casser
    l'inventaire complet du gateway.
    """
    now = time.time()
    with store._connect() as conn:  # vue interne en lecture seule, même package
        rows = conn.execute(
            """
            SELECT
                l.attempt_id,
                l.lease_id,
                l.nonce,
                l.ciphertext,
                l.status,
                l.duration_ms,
                l.finalized_elapsed_ms,
                l.claim_token_hash,
                l.claim_expires_at,
                l.claim_consumed_at,
                l.created_at,
                l.updated_at,
                COUNT(e.sequence) AS event_count
            FROM leases l
            LEFT JOIN journal_events e ON e.attempt_id = l.attempt_id
            GROUP BY l.attempt_id
            ORDER BY l.updated_at DESC
            """
        ).fetchall()

    leases: list[dict[str, Any]] = []
    for row in rows:
        attempt_id = str(row["attempt_id"])
        lease: dict[str, Any] = {}
        runtime_state = "ready"
        try:
            bundle = store.lease_bundle(attempt_id)
            raw_lease = bundle.get("lease")
            lease = raw_lease if isinstance(raw_lease, dict) else {}
        except Exception:
            runtime_state = "corrupt"

        elapsed_ms: int | None = None
        if runtime_state != "corrupt" and row["status"] == "active":
            if attempt_id in store._monotonic_origins:
                try:
                    elapsed_ms = store.elapsed_ms(attempt_id)
                except RuntimeError:
                    runtime_state = "revalidation_required"
            else:
                runtime_state = "revalidation_required"
        elif row["finalized_elapsed_ms"] is not None:
            elapsed_ms = int(row["finalized_elapsed_ms"])

        trace = lease.get("trace") if isinstance(lease.get("trace"), dict) else {}
        question_count = 0
        if runtime_state != "corrupt":
            question_count = int(trace.get("question_count") or len(lease.get("questions") or []))

        leases.append(
            {
                "attempt_id": attempt_id,
                "lease_id": str(row["lease_id"]),
                "status": str(row["status"]),
                "runtime_state": runtime_state,
                "deadline_at": lease.get("deadline_at") if runtime_state != "corrupt" else None,
                "duration_ms": int(row["duration_ms"]),
                "elapsed_ms": elapsed_ms,
                "question_count": question_count,
                "event_count": int(row["event_count"] or 0),
                "claim_state": _claim_state(row, now),
                "claim_expires_at": int(row["claim_expires_at"] or 0) or None,
                "sync_pending": row["status"] == "finalized" and runtime_state != "corrupt",
                "station": _safe_station(lease.get("station")) if runtime_state != "corrupt" else _safe_station(None),
                "created_at": float(row["created_at"]),
                "updated_at": float(row["updated_at"]),
            }
        )

    media_files = 0
    media_bytes = 0
    for path in media.root.iterdir():
        if path.is_file() and not path.name.endswith(".json") and not path.name.startswith(".download-"):
            media_files += 1
            try:
                media_bytes += path.stat().st_size
            except OSError:
                pass

    counts = store.counts()
    return {
        "lease_counts": counts,
        "leases": leases,
        "sync_pending": sum(1 for item in leases if item["sync_pending"]),
        "revalidation_required": sum(1 for item in leases if item["runtime_state"] == "revalidation_required"),
        "corrupt_leases": sum(1 for item in leases if item["runtime_state"] == "corrupt"),
        "media_cache": {"files": media_files, "bytes": media_bytes},
    }

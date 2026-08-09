from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .central import CentralClient
from .media import MediaCache
from .operator_view import build_operator_status
from .release import EdgeReleaseManager
from .store import EdgeStore
from .tickets import media_ticket


class EdgeAgentService:
    def __init__(
        self,
        store: EdgeStore,
        central: CentralClient,
        media: MediaCache,
        release_manager: EdgeReleaseManager | None = None,
    ):
        self.store = store
        self.central = central
        self.media = media
        self.release_manager = release_manager

    def _fleet_telemetry(self) -> dict[str, int]:
        status = self.operator_status()
        counts = status.get("lease_counts") or {}
        media = status.get("media_cache") or {}
        return {
            "active_leases": int(counts.get("active") or 0),
            "finalized_leases": int(counts.get("finalized") or 0),
            "synced_leases": int(counts.get("synced") or 0),
            "sync_pending": int(status.get("sync_pending") or 0),
            "revalidation_required": int(status.get("revalidation_required") or 0),
            "corrupt_leases": int(status.get("corrupt_leases") or 0),
            "media_files": int(media.get("files") or 0),
            "media_bytes": int(media.get("bytes") or 0),
        }

    def activate_attempt(self, attempt_id: str, station_device_key: str, lang: str = "fr") -> dict[str, Any]:
        station_device_key = station_device_key.strip()
        if len(station_device_key) < 4:
            raise ValueError("Identifiant du poste candidat invalide")
        self.heartbeat()
        bundle = self.central.issue_lease(attempt_id, lang)
        if not self.central.verify_lease_bundle(bundle):
            raise RuntimeError("Signature centrale du lease invalide")

        lease = bundle["lease"]
        station_binding = lease.get("station") or {}
        if station_binding.get("device_key") != station_device_key:
            raise RuntimeError("Le lease central n'est pas lié au poste candidat demandé")

        local_bundle = self.media.prefetch_bundle(bundle)
        session = self.store.put_lease(local_bundle, station_device_key)
        return {
            **session,
            "deadline_at": lease["deadline_at"],
            "duration_seconds": lease["duration_seconds"],
            "question_count": len(lease.get("questions", [])),
            "station": station_binding,
        }

    def claim_candidate_session(self, attempt_id: str, claim_token: str, station_key: str) -> dict[str, Any]:
        return self.store.claim_candidate_session(attempt_id, claim_token, station_key)

    def _ticketed_questions(self, attempt_id: str, lease: dict, questions: list[dict]) -> list[dict]:
        rendered = json.loads(json.dumps(questions))
        marker = f"/v1/exams/{attempt_id}/media/"
        deadline = datetime.fromisoformat(str(lease["deadline_at"]).replace("Z", "+00:00"))
        expires_at = int(deadline.timestamp()) + 3600
        for question in rendered:
            for field in ("media_url", "audio_url"):
                value = question.get(field)
                if not isinstance(value, str):
                    continue
                parsed = urlsplit(value)
                if marker not in parsed.path:
                    continue
                digest = parsed.path.rsplit("/", 1)[-1]
                ticket = media_ticket(self.store.storage_key, attempt_id, digest, expires_at)
                query = f"expires={expires_at}&ticket={ticket}"
                question[field] = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))
        return rendered

    def candidate_exam(self, attempt_id: str, access_token: str, station_key: str) -> dict[str, Any]:
        row = self.store.verify_candidate_access(attempt_id, access_token, station_key)
        bundle = self.store.media_safe_bundle(attempt_id)
        lease = bundle["lease"]
        elapsed = self.store.elapsed_ms(attempt_id) if row["status"] == "active" else int(row["finalized_elapsed_ms"] or 0)
        questions = bundle.get("local_questions", lease.get("questions", []))
        return {
            "attempt_id": attempt_id,
            "lease_id": lease["lease_id"],
            "status": row["status"],
            "elapsed_ms": elapsed,
            "duration_ms": int(row["duration_ms"]),
            "remaining_ms": max(0, int(row["duration_ms"]) - elapsed),
            "answers": self.store.current_answers(attempt_id),
            "questions": self._ticketed_questions(attempt_id, lease, questions),
            "language": lease.get("language", "fr"),
            "station": lease.get("station"),
        }

    def answer(self, attempt_id: str, access_token: str, station_key: str, question_id: str, answer: str) -> dict[str, Any]:
        self.store.verify_candidate_access(attempt_id, access_token, station_key)
        event = self.store.append_answer(attempt_id, question_id, answer)
        return {
            "saved": True,
            "sequence": event["sequence"],
            "elapsed_ms": event["elapsed_ms"],
            "journal_head_hash": event["event_hash"],
        }

    def finalize(self, attempt_id: str, access_token: str, station_key: str) -> dict[str, Any]:
        self.store.verify_candidate_access(attempt_id, access_token, station_key)
        proof = self.store.finalize(attempt_id)
        return {**proof, "queued_for_sync": True}

    def sync_attempt(self, attempt_id: str) -> dict[str, Any]:
        self.heartbeat()
        payload = self.store.sync_payload(attempt_id)
        result = self.central.sync_offline(payload)
        if result.get("accepted"):
            self.store.mark_synced(attempt_id)
        return result

    def heartbeat(self) -> dict[str, Any]:
        return self.central.heartbeat(self._fleet_telemetry())

    def release_check(self) -> dict[str, Any]:
        if not self.release_manager:
            raise RuntimeError("Gestionnaire de release Edge non configuré")
        self.heartbeat()
        return self.release_manager.check()

    def release_stage(self) -> dict[str, Any]:
        if not self.release_manager:
            raise RuntimeError("Gestionnaire de release Edge non configuré")
        offer = self.release_check()
        return self.release_manager.stage(offer)

    def release_status(self) -> dict[str, Any]:
        if not self.release_manager:
            return {"enabled": False, "staged": None, "install_receipt": None}
        return {"enabled": True, **self.release_manager.status()}

    def release_attest_install(self) -> dict[str, Any]:
        if not self.release_manager:
            raise RuntimeError("Gestionnaire de release Edge non configuré")
        return self.release_manager.attest_install_receipt()

    def status(self) -> dict[str, Any]:
        """Statut public minimal utilisé par /health."""
        return {"lease_counts": self.store.counts()}

    def operator_status(self) -> dict[str, Any]:
        """Vue détaillée réservée à l'opérateur authentifié du centre."""
        return {
            **build_operator_status(self.store, self.media),
            "release": self.release_status(),
        }

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .central import CentralClient
from .media import MediaCache
from .store import EdgeStore
from .tickets import media_ticket


class EdgeAgentService:
    def __init__(self, store: EdgeStore, central: CentralClient, media: MediaCache):
        self.store = store
        self.central = central
        self.media = media

    def activate_attempt(self, attempt_id: str, station_device_key: str, lang: str = "fr") -> dict[str, Any]:
        if len(station_device_key.strip()) < 4:
            raise ValueError("Identifiant du poste candidat invalide")
        self.central.heartbeat()
        bundle = self.central.issue_lease(attempt_id, lang)
        if not self.central.verify_lease_bundle(bundle):
            raise RuntimeError("Signature centrale du lease invalide")

        # Fail closed : tous les médias du paquet doivent être disponibles sur
        # le LAN avant de déclarer la tentative offline-capable.
        local_bundle = self.media.prefetch_bundle(bundle)
        session = self.store.put_lease(local_bundle, station_device_key.strip())
        lease = local_bundle["lease"]
        return {
            **session,
            "deadline_at": lease["deadline_at"],
            "duration_seconds": lease["duration_seconds"],
            "question_count": len(lease.get("questions", [])),
        }

    def _ticketed_questions(self, attempt_id: str, lease: dict, questions: list[dict]) -> list[dict]:
        rendered = json.loads(json.dumps(questions))
        prefix = f"/v1/exams/{attempt_id}/media/"
        deadline = datetime.fromisoformat(str(lease["deadline_at"]).replace("Z", "+00:00"))
        expires_at = int(deadline.timestamp()) + 3600
        for question in rendered:
            for field in ("media_url", "audio_url"):
                value = question.get(field)
                if not isinstance(value, str) or not value.startswith(prefix):
                    continue
                digest = value[len(prefix):].split("?", 1)[0]
                ticket = media_ticket(self.store.storage_key, attempt_id, digest, expires_at)
                question[field] = f"{prefix}{digest}?expires={expires_at}&ticket={ticket}"
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
            "remaining_ms": max(0, int(row["duration_ms"]) - elapsed),
            "questions": self._ticketed_questions(attempt_id, lease, questions),
            "language": lease.get("language", "fr"),
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
        self.central.heartbeat()
        payload = self.store.sync_payload(attempt_id)
        result = self.central.sync_offline(payload)
        if result.get("accepted"):
            self.store.mark_synced(attempt_id)
        return result

    def heartbeat(self) -> dict[str, Any]:
        return self.central.heartbeat()

    def status(self) -> dict[str, Any]:
        return {"lease_counts": self.store.counts()}

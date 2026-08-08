from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .crypto import compare_secret, decrypt_json, encrypt_json, secret_hash

JOURNAL_GENESIS_HASH = "0" * 64
CLAIM_TTL_SECONDS = 10 * 60


def _canonical_event_hash(
    *,
    lease_id: str,
    sequence: int,
    elapsed_ms: int,
    question_id: str,
    answer: str,
    prev_hash: str,
) -> str:
    payload = {
        "answer": answer,
        "elapsed_ms": int(elapsed_ms),
        "lease_id": lease_id,
        "prev_hash": prev_hash,
        "question_id": question_id,
        "sequence": int(sequence),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _derive_access_token(storage_key: bytes, attempt_id: str, claim_token: str) -> str:
    message = f"coderoute-edge-access-v1\x00{attempt_id}\x00{claim_token}".encode("utf-8")
    digest = hmac.new(storage_key, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class EdgeStore:
    def __init__(self, database_path: Path, storage_key: bytes):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_key = storage_key
        self._lock = threading.RLock()
        self._monotonic_origins: dict[str, tuple[float, int]] = {}
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path, timeout=10, isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        columns = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS leases (
                    attempt_id TEXT PRIMARY KEY,
                    lease_id TEXT NOT NULL UNIQUE,
                    nonce BLOB NOT NULL,
                    ciphertext BLOB NOT NULL,
                    access_token_hash TEXT NOT NULL,
                    station_key_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    base_elapsed_ms INTEGER NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    journal_head_hash TEXT NOT NULL,
                    finalized_elapsed_ms INTEGER,
                    claim_token_hash TEXT,
                    claim_expires_at REAL,
                    claim_consumed_at REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS journal_events (
                    attempt_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    nonce BLOB NOT NULL,
                    ciphertext BLOB NOT NULL,
                    event_hash TEXT NOT NULL,
                    PRIMARY KEY (attempt_id, sequence),
                    FOREIGN KEY(attempt_id) REFERENCES leases(attempt_id) ON DELETE CASCADE
                );
                """
            )
            self._ensure_column(conn, "leases", "claim_token_hash", "TEXT")
            self._ensure_column(conn, "leases", "claim_expires_at", "REAL")
            self._ensure_column(conn, "leases", "claim_consumed_at", "REAL")

    def next_node_sequence(self) -> int:
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT value FROM meta WHERE key='node_sequence'").fetchone()
            value = int(row["value"]) + 1 if row else 1
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('node_sequence',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(value),),
            )
            conn.commit()
            return value

    def put_lease(self, bundle: dict[str, Any], station_key: str) -> dict[str, Any]:
        lease = bundle["lease"]
        attempt_id = str(lease["attempt_id"])
        lease_id = str(lease["lease_id"])
        started = _parse_iso(str(lease["started_at"]))
        issued = _parse_iso(str(lease["issued_at"]))
        base_elapsed_ms = max(0, int((issued - started) * 1000))
        duration_ms = int(lease["duration_seconds"]) * 1000
        claim_token = secrets.token_urlsafe(32)
        access_token = _derive_access_token(self.storage_key, attempt_id, claim_token)
        claim_expires_at = time.time() + CLAIM_TTL_SECONDS
        nonce, ciphertext = encrypt_json(self.storage_key, bundle, aad=f"lease:{lease_id}")
        now = time.time()
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT lease_id FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
            if existing and existing["lease_id"] != lease_id:
                raise RuntimeError("Une autre identité de lease existe déjà pour cette tentative")
            conn.execute(
                """
                INSERT INTO leases(
                    attempt_id,lease_id,nonce,ciphertext,access_token_hash,station_key_hash,status,
                    base_elapsed_ms,duration_ms,journal_head_hash,finalized_elapsed_ms,
                    claim_token_hash,claim_expires_at,claim_consumed_at,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(attempt_id) DO UPDATE SET
                    lease_id=excluded.lease_id,
                    nonce=excluded.nonce,
                    ciphertext=excluded.ciphertext,
                    access_token_hash=excluded.access_token_hash,
                    station_key_hash=excluded.station_key_hash,
                    status='active',
                    base_elapsed_ms=excluded.base_elapsed_ms,
                    duration_ms=excluded.duration_ms,
                    journal_head_hash=excluded.journal_head_hash,
                    finalized_elapsed_ms=NULL,
                    claim_token_hash=excluded.claim_token_hash,
                    claim_expires_at=excluded.claim_expires_at,
                    claim_consumed_at=NULL,
                    updated_at=excluded.updated_at
                """,
                (
                    attempt_id,
                    lease_id,
                    nonce,
                    ciphertext,
                    secret_hash(access_token, domain="edge-access-token"),
                    secret_hash(station_key, domain="edge-station-key"),
                    "active",
                    base_elapsed_ms,
                    duration_ms,
                    JOURNAL_GENESIS_HASH,
                    None,
                    secret_hash(claim_token, domain="edge-claim-token"),
                    claim_expires_at,
                    None,
                    now,
                    now,
                ),
            )
            conn.execute("DELETE FROM journal_events WHERE attempt_id=?", (attempt_id,))
            conn.commit()
        self._monotonic_origins[attempt_id] = (time.monotonic(), base_elapsed_ms)
        return {
            "attempt_id": attempt_id,
            "lease_id": lease_id,
            "claim_token": claim_token,
            "claim_expires_at": int(claim_expires_at),
        }

    def claim_candidate_session(self, attempt_id: str, claim_token: str, station_key: str) -> dict[str, Any]:
        now = time.time()
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
            if not row:
                raise KeyError("Lease local introuvable")
            if row["status"] != "active":
                raise RuntimeError("Le claim n'est disponible que pour une tentative active")
            if not row["claim_token_hash"] or not compare_secret(
                claim_token, row["claim_token_hash"], domain="edge-claim-token"
            ):
                raise PermissionError("Claim Edge invalide")
            if float(row["claim_expires_at"] or 0) < now:
                raise PermissionError("Claim Edge expiré")
            if row["claim_consumed_at"] is not None:
                raise PermissionError("Claim Edge déjà consommé")
            if not compare_secret(station_key, row["station_key_hash"], domain="edge-station-key"):
                raise PermissionError("Ce claim appartient à un autre poste candidat")

            access_token = _derive_access_token(self.storage_key, attempt_id, claim_token)
            if not compare_secret(access_token, row["access_token_hash"], domain="edge-access-token"):
                raise RuntimeError("Dérivation du token Edge incohérente")
            conn.commit()
            return {
                "attempt_id": attempt_id,
                "lease_id": str(row["lease_id"]),
                "access_token": access_token,
                "claim_expires_at": int(row["claim_expires_at"]),
            }

    def verify_candidate_access(self, attempt_id: str, access_token: str, station_key: str) -> sqlite3.Row:
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
            if not row:
                raise KeyError("Lease local introuvable")
            if not compare_secret(access_token, row["access_token_hash"], domain="edge-access-token"):
                raise PermissionError("Token de session Edge invalide")
            if not compare_secret(station_key, row["station_key_hash"], domain="edge-station-key"):
                raise PermissionError("Poste candidat différent de celui activé")
            if row["claim_consumed_at"] is None:
                now = time.time()
                conn.execute(
                    "UPDATE leases SET claim_consumed_at=?,updated_at=? WHERE attempt_id=?",
                    (now, now, attempt_id),
                )
                row = conn.execute("SELECT * FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
            conn.commit()
            return row

    def lease_bundle(self, attempt_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
        if not row:
            raise KeyError("Lease local introuvable")
        return decrypt_json(
            self.storage_key,
            row["nonce"],
            row["ciphertext"],
            aad=f"lease:{row['lease_id']}",
        )

    def elapsed_ms(self, attempt_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT base_elapsed_ms,duration_ms,status FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
        if not row:
            raise KeyError("Lease local introuvable")
        origin = self._monotonic_origins.get(attempt_id)
        if origin is None:
            raise RuntimeError("EDGE_REVALIDATION_REQUIRED")
        monotonic_start, base_elapsed = origin
        current = base_elapsed + int((time.monotonic() - monotonic_start) * 1000)
        return max(int(row["base_elapsed_ms"]), current)

    def append_answer(self, attempt_id: str, question_id: str, answer: str) -> dict[str, Any]:
        bundle = self.lease_bundle(attempt_id)
        lease = bundle["lease"]
        question_map = {str(question["id"]): question for question in lease.get("questions", [])}
        question = question_map.get(question_id)
        if not question:
            raise ValueError("Question hors lease")
        if answer not in [str(option) for option in question.get("options", [])]:
            raise ValueError("Réponse hors options du lease")

        elapsed = self.elapsed_ms(attempt_id)
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            lease_row = conn.execute("SELECT * FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
            if not lease_row:
                raise KeyError("Lease local introuvable")
            if lease_row["status"] != "active":
                raise RuntimeError("Le lease n'accepte plus de réponse")
            if elapsed > int(lease_row["duration_ms"]) + 2000:
                raise RuntimeError("Deadline Edge dépassée")
            last = conn.execute(
                "SELECT sequence,event_hash FROM journal_events WHERE attempt_id=? ORDER BY sequence DESC LIMIT 1",
                (attempt_id,),
            ).fetchone()
            sequence = int(last["sequence"]) + 1 if last else 1
            prev_hash = str(last["event_hash"]) if last else JOURNAL_GENESIS_HASH
            event_hash = _canonical_event_hash(
                lease_id=str(lease_row["lease_id"]),
                sequence=sequence,
                elapsed_ms=elapsed,
                question_id=question_id,
                answer=answer,
                prev_hash=prev_hash,
            )
            event = {
                "sequence": sequence,
                "elapsed_ms": elapsed,
                "question_id": question_id,
                "answer": answer,
                "prev_hash": prev_hash,
                "event_hash": event_hash,
            }
            nonce, ciphertext = encrypt_json(self.storage_key, event, aad=f"event:{attempt_id}:{sequence}")
            conn.execute(
                "INSERT INTO journal_events(attempt_id,sequence,nonce,ciphertext,event_hash) VALUES(?,?,?,?,?)",
                (attempt_id, sequence, nonce, ciphertext, event_hash),
            )
            conn.execute(
                "UPDATE leases SET journal_head_hash=?,updated_at=? WHERE attempt_id=?",
                (event_hash, time.time(), attempt_id),
            )
            conn.commit()
        return event

    def current_answers(self, attempt_id: str) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT sequence,nonce,ciphertext FROM journal_events WHERE attempt_id=? ORDER BY sequence ASC",
                (attempt_id,),
            ).fetchall()
        answers: dict[str, str] = {}
        for row in rows:
            event = decrypt_json(
                self.storage_key,
                row["nonce"],
                row["ciphertext"],
                aad=f"event:{attempt_id}:{row['sequence']}",
            )
            answers[str(event["question_id"])] = str(event["answer"])
        return answers

    def finalize(self, attempt_id: str) -> dict[str, Any]:
        elapsed = self.elapsed_ms(attempt_id)
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
            if not row:
                raise KeyError("Lease local introuvable")
            if row["status"] == "finalized":
                elapsed = int(row["finalized_elapsed_ms"])
            elif row["status"] != "active":
                raise RuntimeError("Lease déjà fermé")
            elif elapsed > int(row["duration_ms"]) + 2000:
                raise RuntimeError("Deadline Edge dépassée")
            else:
                conn.execute(
                    "UPDATE leases SET status='finalized',finalized_elapsed_ms=?,updated_at=? WHERE attempt_id=?",
                    (elapsed, time.time(), attempt_id),
                )
                conn.commit()
            return {
                "attempt_id": attempt_id,
                "lease_id": str(row["lease_id"]),
                "finalized_elapsed_ms": elapsed,
                "journal_head_hash": str(row["journal_head_hash"]),
            }

    def sync_payload(self, attempt_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            lease_row = conn.execute("SELECT * FROM leases WHERE attempt_id=?", (attempt_id,)).fetchone()
            event_rows = conn.execute(
                "SELECT sequence,nonce,ciphertext FROM journal_events WHERE attempt_id=? ORDER BY sequence ASC",
                (attempt_id,),
            ).fetchall()
        if not lease_row:
            raise KeyError("Lease local introuvable")
        if lease_row["status"] not in {"finalized", "synced"}:
            raise RuntimeError("La tentative locale doit être finalisée avant synchronisation")
        events = [
            decrypt_json(
                self.storage_key,
                event["nonce"],
                event["ciphertext"],
                aad=f"event:{attempt_id}:{event['sequence']}",
            )
            for event in event_rows
        ]
        return {
            "lease_id": str(lease_row["lease_id"]),
            "finalized_elapsed_ms": int(lease_row["finalized_elapsed_ms"] or 0),
            "journal_head_hash": str(lease_row["journal_head_hash"]),
            "events": events,
        }

    def mark_synced(self, attempt_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE leases SET status='synced',updated_at=? WHERE attempt_id=?",
                (time.time(), attempt_id),
            )

    def counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute("SELECT status,COUNT(*) AS n FROM leases GROUP BY status").fetchall()
        return {str(row["status"]): int(row["n"]) for row in rows}

    def media_safe_bundle(self, attempt_id: str) -> dict[str, Any]:
        return self.lease_bundle(attempt_id)


def _parse_iso(value: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()

"""
Rate limiter de login persistant via PostgreSQL.

Utilise une table `login_rate_limit` pour résister aux redémarrages de conteneur.
En cas d'erreur DB (indisponibilité passagère), repli automatique sur le compteur
in-memory pour ne pas bloquer les connexions légitimes.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class _InMemoryFallback:
    """Compteur in-memory utilisé si la DB est indisponible."""

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def is_blocked(self, key: str) -> bool:
        return len(self._recent(key)) >= self.max_attempts

    def register_failure(self, key: str) -> None:
        self._recent(key).append(monotonic())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def clear(self) -> None:
        self._attempts.clear()

    def _recent(self, key: str) -> deque[float]:
        q = self._attempts[key]
        cutoff = monotonic() - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        return q


class LoginRateLimiter:
    """
    Rate limiter de login persistant.

    Stratégie : écriture PostgreSQL avec repli transparent sur in-memory.
    La table `login_rate_limit` est créée au premier usage si elle n'existe pas.
    """

    _table_ensured: bool = False

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._fallback = _InMemoryFallback(max_attempts, window_seconds)

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @max_attempts.setter
    def max_attempts(self, value: int) -> None:
        self._max_attempts = value
        self._fallback.max_attempts = value

    # ── Interface publique ─────────────────────────────────────────────────

    def is_blocked(self, key: str, db: Session | None = None) -> bool:
        if db is None:
            return self._fallback.is_blocked(key)
        try:
            self._ensure_table(db)
            return self._db_count(db, key) >= self._max_attempts
        except Exception:
            return self._fallback.is_blocked(key)

    def register_failure(self, key: str, db: Session | None = None) -> None:
        if db is None:
            self._fallback.register_failure(key)
            return
        try:
            self._ensure_table(db)
            self._db_insert(db, key)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            self._fallback.register_failure(key)

    def reset(self, key: str, db: Session | None = None) -> None:
        if db is None:
            self._fallback.reset(key)
            return
        try:
            self._ensure_table(db)
            self._db_delete(db, key)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            self._fallback.reset(key)

    def clear(self) -> None:
        self._fallback.clear()

    # ── Opérations DB ─────────────────────────────────────────────────────

    def _ensure_table(self, db: Session) -> None:
        if LoginRateLimiter._table_ensured:
            return
        from sqlalchemy import text

        # SQL PORTABLE (PostgreSQL et SQLite). L'ancienne version utilisait
        # SERIAL / TIMESTAMPTZ / NOW(), spécifiques à PostgreSQL : sur toute
        # autre base, la création échouait et le limiteur retombait
        # SILENCIEUSEMENT sur un compteur en mémoire — donc propre à chaque
        # worker, et contournable en tombant sur un autre worker.
        dialect = db.bind.dialect.name if db.bind is not None else "postgresql"
        if dialect == "postgresql":
            create_sql = """
                CREATE TABLE IF NOT EXISTS login_rate_limit (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) NOT NULL,
                    attempted_at TIMESTAMP NOT NULL
                )
            """
        else:
            create_sql = """
                CREATE TABLE IF NOT EXISTS login_rate_limit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key VARCHAR(255) NOT NULL,
                    attempted_at TIMESTAMP NOT NULL
                )
            """
        db.execute(text(create_sql))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_login_rate_limit_key_time "
            "ON login_rate_limit (key, attempted_at)"
        ))
        db.commit()
        LoginRateLimiter._table_ensured = True

    def _cutoff(self) -> datetime:
        # Naïf (sans fuseau) pour rester comparable sur les deux moteurs
        return (datetime.now(UTC) - timedelta(seconds=self.window_seconds)).replace(tzinfo=None)

    def _db_count(self, db: Session, key: str) -> int:
        from sqlalchemy import text
        row = db.execute(
            text("SELECT COUNT(*) FROM login_rate_limit WHERE key = :key AND attempted_at > :cutoff"),
            {"key": key, "cutoff": self._cutoff()},
        ).fetchone()
        return int(row[0]) if row else 0

    def _db_insert(self, db: Session, key: str) -> None:
        from sqlalchemy import text
        # L'horodatage est fourni par l'application (et non NOW(), spécifique
        # à PostgreSQL) : portable et cohérent avec _cutoff().
        now = datetime.now(UTC).replace(tzinfo=None)
        db.execute(
            text("INSERT INTO login_rate_limit (key, attempted_at) VALUES (:key, :now)"),
            {"key": key, "now": now},
        )
        # Nettoyage des anciennes entrées (hors fenêtre × 2 pour marge)
        db.execute(
            text("DELETE FROM login_rate_limit WHERE attempted_at < :cutoff"),
            {"cutoff": (datetime.now(UTC) - timedelta(seconds=self.window_seconds * 2)).replace(tzinfo=None)},
        )

    def _db_delete(self, db: Session, key: str) -> None:
        from sqlalchemy import text
        db.execute(
            text("DELETE FROM login_rate_limit WHERE key = :key"),
            {"key": key},
        )

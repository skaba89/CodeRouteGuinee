"""
Logging structuré JSON — CodeRoute Guinée

Produit des logs JSON parsables par Datadog, Grafana Loki, Cloud Logging, etc.
En développement, affiche des logs colorés lisibles.

Usage :
    from app.logging_config import setup_logging, get_logger
    setup_logging()
    log = get_logger(__name__)
    log.info("session_créée", session_id=sid, center_id=cid, capacity=35)
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formateur JSON structuré — un objet JSON par ligne."""

    LEVEL_MAP = {
        logging.DEBUG:    "debug",
        logging.INFO:     "info",
        logging.WARNING:  "warning",
        logging.ERROR:    "error",
        logging.CRITICAL: "critical",
    }

    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "ts":      datetime.now(UTC).isoformat(),
            "level":   self.LEVEL_MAP.get(record.levelno, "info"),
            "logger":  record.name,
            "msg":     record.getMessage(),
            "service": "coderoute-api",
            "env":     os.environ.get("ENVIRONMENT", "development"),
        }

        # Champs contextuels injectés via LoggerAdapter ou extra={}
        for key in ("user_id", "role", "center_id", "session_id",
                    "attempt_id", "path", "method", "status", "duration_ms",
                    "candidate_id", "payment_id", "ip"):
            if (val := getattr(record, key, None)) is not None:
                log[key] = val

        # Exception
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
            log["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None

        # Champs extra arbitraires
        std_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "taskName",
            "message",
        }
        for k, v in record.__dict__.items():
            if k not in std_attrs and not k.startswith("_"):
                log.setdefault(k, v)

        return json.dumps(log, ensure_ascii=False, default=str)


class DevFormatter(logging.Formatter):
    """Formateur coloré pour le développement local."""

    COLORS = {
        "debug":    "\033[36m",   # cyan
        "info":     "\033[32m",   # vert
        "warning":  "\033[33m",   # jaune
        "error":    "\033[31m",   # rouge
        "critical": "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname.lower()
        color = self.COLORS.get(level, "")
        ts = datetime.now().strftime("%H:%M:%S")
        msg = record.getMessage()
        line = f"{color}{ts} [{level.upper():8}]{self.RESET} {record.name}: {msg}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging(level: str | None = None) -> None:
    """Configure le logging global. Appeler une seule fois au démarrage."""
    env = os.environ.get("ENVIRONMENT", "development")
    log_level = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))

    # Supprimer les handlers existants
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level, logging.INFO))

    if env == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(DevFormatter())

    root.addHandler(handler)

    # Réduire le bruit des librairies tierces
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "passlib", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger nommé pour un module."""
    return logging.getLogger(name)


class RequestLogger:
    """
    Middleware de logging des requêtes HTTP.
    Logue chaque requête avec durée, statut et user_id si authentifié.
    """

    def __init__(self, app):
        self.app = app
        self.log = get_logger("coderoute.http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time
        start = time.perf_counter()
        method = scope.get("method", "")
        path = scope.get("path", "")
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            level = "warning" if status_code >= 400 else "info"
            # Ignorer les health checks pour réduire le bruit
            if path not in ("/health", "/health/readiness"):
                getattr(self.log, level)(
                    f"{method} {path} → {status_code}",
                    extra={
                        "method":      method,
                        "path":        path,
                        "status":      status_code,
                        "duration_ms": duration_ms,
                    }
                )

"""Sentry wrapper CodeRoute — dégradation gracieuse et privacy-safe P11."""
from __future__ import annotations

import logging
import os
from typing import Any

from app.soc_privacy import pseudonymize, sanitize_context, sanitize_free_text

log = logging.getLogger("coderoute.sentry")

_SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
_ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
_TRACES_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
_sentry_sdk: Any = None


def init_sentry() -> bool:
    global _sentry_sdk
    if not _SENTRY_DSN:
        log.info("Sentry désactivé (SENTRY_DSN absent)")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            environment=_ENVIRONMENT,
            traces_sample_rate=_TRACES_RATE,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            send_default_pii=False,
            ignore_errors=[KeyboardInterrupt, SystemExit],
        )
        _sentry_sdk = sentry_sdk
        log.info("Sentry initialisé", extra={"environment": _ENVIRONMENT})
        return True
    except ImportError:
        log.warning("sentry-sdk non installé — monitoring désactivé")
        return False
    except Exception as exc:
        log.error("Erreur init Sentry: %s", exc.__class__.__name__)
        return False


def capture_exception(
    exc: Exception,
    context: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    safe_context = sanitize_context(context)
    if _sentry_sdk:
        with _sentry_sdk.push_scope() as scope:
            for key, value in safe_context.items():
                scope.set_extra(key, value)
            if user_id:
                scope.set_user({"id": pseudonymize(user_id, "usr")})
            _sentry_sdk.capture_exception(exc)
    else:
        log.error(
            "Exception capturée (Sentry inactif): %s",
            exc.__class__.__name__,
            extra={"context": safe_context},
        )


def capture_message(
    message: str,
    level: str = "info",
    context: dict[str, Any] | None = None,
) -> None:
    safe_message = sanitize_free_text(message)
    safe_context = sanitize_context(context)
    if _sentry_sdk:
        with _sentry_sdk.push_scope() as scope:
            for key, value in safe_context.items():
                scope.set_extra(key, value)
            _sentry_sdk.capture_message(safe_message, level=level)
    else:
        getattr(log, level, log.info)("Sentry message: %s", safe_message, extra={"context": safe_context})


def is_active() -> bool:
    return _sentry_sdk is not None

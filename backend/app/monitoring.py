"""Monitoring applicatif CodeRoute Guinée — Sentry privacy-safe."""
from __future__ import annotations

import logging

from app.soc_privacy import pseudonymize, sanitize_context

logger = logging.getLogger(__name__)


def init_sentry(
    dsn: str | None,
    environment: str = "development",
    release: str = "0.14.0",
    traces_sample_rate: float = 0.2,
) -> bool:
    if not dsn:
        logger.info("Sentry désactivé (SENTRY_DSN absent)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
            ],
            before_send=_filter_expected_errors,
            send_default_pii=False,
        )
        logger.info("Sentry initialisé — environment=%s release=%s", environment, release)
        return True
    except ImportError:
        logger.warning("sentry-sdk non installé — monitoring Sentry désactivé")
        return False


def _filter_expected_errors(event: dict, hint: dict) -> dict | None:
    exc_info = hint.get("exc_info")
    if exc_info:
        exc_type, exc_value, _ = exc_info
        if exc_type and exc_type.__name__ == "HTTPException":
            status_code = getattr(exc_value, "status_code", 500)
            if status_code < 500:
                return None
        if exc_type and exc_type.__name__ in ("ValidationError", "RequestValidationError"):
            return None
    # Défense supplémentaire : supprimer tout bloc user brut hérité d'une intégration.
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = sanitize_context(user)
    extra = event.get("extra")
    if isinstance(extra, dict):
        event["extra"] = sanitize_context(extra)
    request = event.get("request")
    if isinstance(request, dict):
        # URL/query/body ne doivent pas sortir vers Sentry depuis P11.
        event["request"] = {
            key: value
            for key, value in sanitize_context(request).items()
            if key not in {"data", "query_string", "cookies", "headers", "url"}
        }
    return event


def capture_exception(exc: Exception, context: dict | None = None) -> None:
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in sanitize_context(context).items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        logger.error("Exception non capturée dans Sentry (sdk absent): %s", exc)


def set_user_context(user_id: str, role: str, email: str | None = None) -> None:
    """Corrélation Sentry pseudonymisée. `email` est ignoré volontairement."""
    del email
    try:
        import sentry_sdk
        sentry_sdk.set_user({"id": pseudonymize(user_id, "usr"), "role": role})
    except ImportError:
        pass

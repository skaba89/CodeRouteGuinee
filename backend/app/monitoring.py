"""
Monitoring applicatif CodeRoute Guinée.

Intègre Sentry pour la remontée automatique des erreurs en production.
L'initialisation est conditionnelle à la présence de SENTRY_DSN dans les variables
d'environnement — sans DSN, le module est silencieusement désactivé (safe for dev/test).

Variables d'environnement :
  SENTRY_DSN           — DSN fourni par Sentry (obligatoire pour activer)
  SENTRY_ENVIRONMENT   — 'production' / 'staging' (défaut : valeur de ENVIRONMENT)
  SENTRY_SAMPLE_RATE   — Taux d'échantillonnage traces (0.0–1.0, défaut : 0.2)
  SENTRY_RELEASE       — Version de l'app (défaut : version FastAPI)

Obtenir un DSN : https://sentry.io → New Project → FastAPI
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def init_sentry(
    dsn: str | None,
    environment: str = "development",
    release: str = "0.14.0",
    traces_sample_rate: float = 0.2,
) -> bool:
    """
    Initialise Sentry si un DSN est fourni.

    Returns True si Sentry est activé, False sinon.
    """
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
                LoggingIntegration(
                    level=logging.WARNING,   # Capture les logs WARNING+
                    event_level=logging.ERROR,  # Crée des événements pour ERROR+
                ),
            ],
            # Ne pas capturer les erreurs 4xx (validation, auth) — uniquement 5xx
            before_send=_filter_expected_errors,
            # Données sensibles à ne jamais envoyer à Sentry
            send_default_pii=False,
        )
        logger.info("Sentry initialisé — environment=%s release=%s", environment, release)
        return True

    except ImportError:
        logger.warning(
            "sentry-sdk non installé — ajouter 'sentry-sdk[fastapi]' à requirements.txt "
            "pour activer le monitoring. SENTRY_DSN défini mais ignoré."
        )
        return False


def _filter_expected_errors(event: dict, hint: dict) -> dict | None:
    """
    Filtre les erreurs attendues pour ne pas saturer Sentry.

    - HTTPException 4xx : erreurs client normales (401, 403, 404, 422, 429)
    - Exceptions de validation Pydantic : déjà gérées par FastAPI
    """
    exc_info = hint.get("exc_info")
    if exc_info:
        exc_type, exc_value, _ = exc_info
        # Filtrer HTTPException 4xx
        if exc_type and exc_type.__name__ == "HTTPException":
            status_code = getattr(exc_value, "status_code", 500)
            if status_code < 500:
                return None
        # Filtrer ValidationError Pydantic
        if exc_type and exc_type.__name__ in ("ValidationError", "RequestValidationError"):
            return None
    return event


def capture_exception(exc: Exception, context: dict | None = None) -> None:
    """
    Capture manuellement une exception dans Sentry.

    Usage :
        from app.monitoring import capture_exception
        try:
            result = risky_operation()
        except Exception as exc:
            capture_exception(exc, {"payment_reference": ref, "provider": provider})
            raise
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        logger.error("Exception non capturée dans Sentry (sdk absent): %s", exc)


def set_user_context(user_id: str, role: str, email: str | None = None) -> None:
    """
    Associe l'utilisateur courant à la session Sentry (pour enrichir les rapports).

    Appelé depuis le middleware d'auth — n'expose jamais le mot de passe.
    """
    try:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id, "role": role, "email": email})
    except ImportError:
        pass

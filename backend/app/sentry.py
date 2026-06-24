"""
Sentry wrapper — CodeRoute Guinée
Dégradation gracieuse si SENTRY_DSN est absent (dev/staging).

En prod : pip install sentry-sdk + SENTRY_DSN dans .env
En dev  : aucun import sentry-sdk, aucune erreur, logs console seulement

Usage :
    from app.sentry import capture_exception, capture_message, init_sentry

    init_sentry()   # à appeler au démarrage (main.py)
    capture_exception(err, context={"user_id": "abc", "action": "submit_exam"})
    capture_message("Paiement Wave webhook reçu", level="info")
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("coderoute.sentry")

_SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
_ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
_TRACES_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

_sentry_sdk: Any = None


def init_sentry() -> bool:
    """
    Initialise Sentry si SENTRY_DSN est configuré et sentry-sdk installé.
    Retourne True si Sentry est actif, False sinon.
    """
    global _sentry_sdk

    if not _SENTRY_DSN:
        log.info("Sentry désactivé (SENTRY_DSN absent)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn                  = _SENTRY_DSN,
            environment          = _ENVIRONMENT,
            traces_sample_rate   = _TRACES_RATE,
            integrations         = [FastApiIntegration(), SqlalchemyIntegration()],
            # Données PII — ne pas envoyer les emails ou IPs
            send_default_pii     = False,
            # Ignorer les erreurs non critiques
            ignore_errors        = [KeyboardInterrupt, SystemExit],
        )
        _sentry_sdk = sentry_sdk
        log.info("✅ Sentry initialisé (env=%s, traces=%.0f%%)",
                 _ENVIRONMENT, _TRACES_RATE * 100)
        return True
    except ImportError:
        log.warning(
            "sentry-sdk non installé — ajouter sentry-sdk à requirements.txt "
            "et définir SENTRY_DSN pour activer le monitoring en production."
        )
        return False
    except Exception as exc:
        log.error("Erreur init Sentry : %s", exc)
        return False


def capture_exception(
    exc: Exception,
    context: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    """
    Capture une exception et l'envoie à Sentry.
    En dev (sans Sentry) : log l'erreur en console.
    """
    if _sentry_sdk:
        with _sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            if user_id:
                scope.set_user({"id": user_id})
            _sentry_sdk.capture_exception(exc)
    else:
        log.error(
            "Exception capturée (Sentry inactif) : %s | context=%s",
            exc, context or {}
        )


def capture_message(
    message: str,
    level: str = "info",
    context: dict[str, Any] | None = None,
) -> None:
    """
    Envoie un message à Sentry.
    En dev : log le message en console.
    """
    if _sentry_sdk:
        with _sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            _sentry_sdk.capture_message(message, level=level)
    else:
        getattr(log, level, log.info)("Sentry message : %s | %s", message, context or {})


def is_active() -> bool:
    """Retourne True si Sentry est actif."""
    return _sentry_sdk is not None

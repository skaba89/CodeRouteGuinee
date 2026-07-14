"""
Test — rédaction des données sensibles dans les logs.

Les logs sont conservés, transmis à Sentry et potentiellement consultés par
des tiers. Un secret ou une donnée personnelle qui y atterrit en clair est une
fuite — et un manquement RGPD pour des données de citoyens guinéens.

L'audit avait trouvé une fuite réelle : les numéros de téléphone des candidats
étaient loggués en clair (orange_sms.py).
"""
from __future__ import annotations

import logging

import pytest

from app.logging_config import RedactionFilter, redact_text, redact_value

REDACTED = "***REDACTED***"


# ── Secrets dans le texte ───────────────────────────────────────────────────

@pytest.mark.parametrize("texte", [
    "Token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4",
    "Authorization: Bearer abc123XYZsecrettoken456",
    "Clé: xkeysib-a1b2c3d4e5f6a7b8c9d0",
    "Stripe sk_live_abcdef123456789",
    "password=MonMotDePasse123",
    "api_key: cle-super-secrete-123",
])
def test_secrets_masques_dans_le_texte(texte: str) -> None:
    resultat = redact_text(texte)
    assert REDACTED in resultat


def test_telephone_masque() -> None:
    """Donnée personnelle : seuls les 3 derniers chiffres restent."""
    assert redact_text("SMS envoyé → +224 622 45 67 89") == "SMS envoyé → ***789"
    assert "622456789" not in redact_text("Appel 622456789")


def test_email_reduit_au_domaine() -> None:
    assert redact_text("Candidat ousmane@gmail.com") == "Candidat ***@gmail.com"


# ── Pas de faux positifs : les logs doivent rester lisibles ─────────────────

@pytest.mark.parametrize("texte", [
    "Score: 36/40",
    "Session 2026-07-11",
    "Durée 30 min",
    "200 questions actives",
    "Référence GN-CODE-2026-000051",
])
def test_donnees_non_sensibles_preservees(texte: str) -> None:
    assert redact_text(texte) == texte


# ── Rédaction par nom de champ ──────────────────────────────────────────────

@pytest.mark.parametrize("cle", [
    "password", "access_token", "csrf_secret", "api_key",
    "authorization", "identity_number",
])
def test_champ_sensible_masque(cle: str) -> None:
    assert redact_value(cle, "valeur-secrete") == REDACTED


def test_champ_normal_preserve() -> None:
    assert redact_value("city", "Conakry") == "Conakry"


def test_dictionnaire_imbrique_masque() -> None:
    entree = {"user": "ali", "password": "x", "nested": {"api_key": "sk_live_abc123456"}}
    sortie = redact_value("payload", entree)
    assert sortie["user"] == "ali"
    assert sortie["password"] == REDACTED
    assert sortie["nested"]["api_key"] == REDACTED


# ── Intégration : le filtre s'applique réellement aux logs ──────────────────

def test_filtre_applique_au_record(caplog) -> None:
    logger = logging.getLogger("test.redaction")
    logger.addFilter(RedactionFilter())
    with caplog.at_level(logging.INFO, logger="test.redaction"):
        logger.info("Connexion avec password=SuperSecret123")
    assert "SuperSecret123" not in caplog.text
    assert REDACTED in caplog.text


def test_filtre_masque_les_champs_extra(caplog) -> None:
    logger = logging.getLogger("test.redaction.extra")
    logger.addFilter(RedactionFilter())
    with caplog.at_level(logging.INFO, logger="test.redaction.extra"):
        logger.info("Requête", extra={"access_token": "eyJsecret", "city": "Conakry"})
    record = caplog.records[-1]
    assert record.access_token == REDACTED
    assert record.city == "Conakry"


def test_filtre_ne_casse_jamais_le_log() -> None:
    """Un log ne doit JAMAIS faire planter l'application, même sur données exotiques."""
    f = RedactionFilter()
    record = logging.LogRecord("t", logging.INFO, "p", 1, "msg %s", (object(),), None)
    assert f.filter(record) is True

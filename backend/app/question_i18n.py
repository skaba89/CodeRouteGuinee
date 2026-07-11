"""
Résolution multilingue du contenu des questions.

Le français (colonnes text/options/explanation) est la source de référence.
Si une traduction existe pour la langue demandée, elle est utilisée ;
sinon on retombe proprement sur le français. Aucune question n'est jamais
vide, quelle que soit la langue.
"""
from __future__ import annotations

from typing import Any

# Langues nationales supportées (alignées sur l'i18n frontend)
SUPPORTED_LANGUAGES = {"fr", "ff", "man", "sus", "kss", "gkp", "lom", "en"}
DEFAULT_LANGUAGE = "fr"


def resolve_question_content(question: Any, lang: str | None) -> dict:
    """
    Retourne {text, options, explanation} dans la langue demandée, avec
    repli sur le français champ par champ (une traduction partielle reste
    utilisable : les champs non traduits restent en français).
    """
    # Base française (référence)
    base_options = question.options
    if isinstance(base_options, str) and base_options.startswith("["):
        import json
        try:
            base_options = json.loads(base_options)
        except (ValueError, TypeError):
            base_options = [base_options]

    result = {
        "text": question.text,
        "options": base_options,
        "explanation": question.explanation,
    }

    if not lang or lang == DEFAULT_LANGUAGE or lang not in SUPPORTED_LANGUAGES:
        return result

    translations = getattr(question, "translations", None) or {}
    tr = translations.get(lang)
    if not isinstance(tr, dict):
        return result

    # Repli champ par champ : n'écrase que ce qui est réellement traduit
    if tr.get("text"):
        result["text"] = tr["text"]
    if isinstance(tr.get("options"), list) and len(tr["options"]) == len(base_options):
        # On ne remplace les options que si le nombre correspond (sécurité :
        # les indices de réponse doivent rester cohérents)
        result["options"] = tr["options"]
    if tr.get("explanation"):
        result["explanation"] = tr["explanation"]

    return result


def available_languages(question: Any) -> list[str]:
    """Langues réellement disponibles pour une question (fr + traductions)."""
    langs = [DEFAULT_LANGUAGE]
    translations = getattr(question, "translations", None) or {}
    for code in translations:
        if code in SUPPORTED_LANGUAGES and code != DEFAULT_LANGUAGE:
            langs.append(code)
    return langs

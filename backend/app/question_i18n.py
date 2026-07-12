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
    Retourne {text, options, explanation, audio_url} pour une question.

    CHOIX DE CONCEPTION — l'écrit reste en français, l'oral suit la langue :

      • Le TEXTE affiché est TOUJOURS en français. Les langues nationales
        guinéennes (Pular, Malinké, Soussou…) n'ont pas de standard
        d'écriture largement partagé : un texte écrit dans ces langues
        dérouterait plus qu'il n'aiderait, et introduirait un risque
        d'ambiguïté juridique sur le sens des questions.

      • L'AUDIO suit la langue du candidat (audio_url : enregistrement par
        un locuteur natif). C'est le canal qui porte réellement la valeur :
        une grande part de la population PARLE ces langues sans les LIRE.

    Un candidat pular voit donc la question en français et l'ENTEND en
    pular. Si aucun enregistrement n'existe, le client retombe sur la
    synthèse vocale : aucune question n'est jamais muette.
    """
    # Le texte de référence (français) est toujours celui qui est affiché.
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
        "audio_url": None,
    }

    if not lang or lang == DEFAULT_LANGUAGE or lang not in SUPPORTED_LANGUAGES:
        return result

    translations = getattr(question, "translations", None) or {}
    tr = translations.get(lang)
    if not isinstance(tr, dict):
        return result

    # Seul l'audio est localisé. Le texte, les options et l'explication
    # restent en français (voir le choix de conception ci-dessus).
    if tr.get("audio_url"):
        result["audio_url"] = tr["audio_url"]

    return result


def available_languages(question: Any) -> list[str]:
    """Langues réellement disponibles pour une question (fr + traductions)."""
    langs = [DEFAULT_LANGUAGE]
    translations = getattr(question, "translations", None) or {}
    for code in translations:
        if code in SUPPORTED_LANGUAGES and code != DEFAULT_LANGUAGE:
            langs.append(code)
    return langs

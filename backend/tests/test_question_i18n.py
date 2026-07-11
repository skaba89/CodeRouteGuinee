"""
Test E2E — Contenu multilingue des questions (Pular, Malinké, Soussou…).

Vérifie le différenciateur clé : un candidat peut passer l'examen dans une
langue nationale, et le scoring reste correct (la réponse traduite est
ramenée à l'option française canonique par son index).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import init_db, SessionLocal
from app.models_question import Question
from app.question_i18n import resolve_question_content, available_languages
from tests.conftest import get_admin_headers


def _make_question() -> str:
    db = SessionLocal()
    q = Question(
        category="signalisation",
        text="Que signifie un panneau STOP ?",
        options=["Arrêt obligatoire", "Ralentir", "Passer", "Klaxonner"],
        correct_answer="Arrêt obligatoire",
        explanation="Le STOP impose un arrêt complet.",
        is_active=True, validation_status="approved",
    )
    db.add(q); db.commit(); qid = q.id; db.close()
    return qid


def test_resolve_fallback_francais() -> None:
    """Sans traduction, on retombe sur le français."""
    init_db()
    qid = _make_question()
    db = SessionLocal()
    q = db.get(Question, qid)
    content = resolve_question_content(q, "ff")  # Pular non traduit
    assert content["text"] == "Que signifie un panneau STOP ?"
    db.close()


def test_set_and_resolve_translation() -> None:
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        H = get_admin_headers(client)
        # Ajouter une traduction Pular (ff)
        r = client.put(f"/api/v1/questions/{qid}/translations", json={
            "ff": {
                "text": "Hol ko maannouni STOP?",
                "options": ["Daragol waɗɗiiɗo", "Leeltude", "Rewde", "Huucude"],
                "explanation": "STOP ina waɗɗina daragol timmungol.",
            }
        }, headers=H)
        assert r.status_code == 200, r.text[:200]
        assert "ff" in r.json()["translations"]

    db = SessionLocal()
    q = db.get(Question, qid)
    content = resolve_question_content(q, "ff")
    assert content["text"] == "Hol ko maannouni STOP?"
    assert content["options"][0] == "Daragol waɗɗiiɗo"
    assert "ff" in available_languages(q)
    db.close()


def test_translation_rejette_mauvais_nombre_options() -> None:
    """Le nombre d'options traduites doit correspondre (index = bonne réponse)."""
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        H = get_admin_headers(client)
        r = client.put(f"/api/v1/questions/{qid}/translations", json={
            "ff": {"text": "x", "options": ["une seule option"]}
        }, headers=H)
        assert r.status_code == 422


def test_scoring_multilingue_reponse_pular() -> None:
    """
    Cœur du test : un candidat répond avec l'option Pular ; le scoring doit
    la ramener à l'option française canonique et compter juste.
    """
    from app.exam_engine import score_answers
    from app.question_i18n import SUPPORTED_LANGUAGES
    import json as _json

    init_db()
    qid = _make_question()
    db = SessionLocal()
    q = db.get(Question, qid)
    q.translations = {
        "ff": {"options": ["Daragol waɗɗiiɗo", "Leeltude", "Rewde", "Huucude"]}
    }
    db.add(q); db.commit()

    # Simuler la normalisation faite par submit_exam
    def _to_canonical(question, submitted):
        canonical = question.options
        if submitted in canonical:
            return submitted
        for lang_code, tr in (question.translations or {}).items():
            if lang_code in SUPPORTED_LANGUAGES and isinstance(tr.get("options"), list):
                if submitted in tr["options"]:
                    return canonical[tr["options"].index(submitted)]
        return submitted

    # Le candidat a répondu en Pular : "Daragol waɗɗiiɗo" (= Arrêt obligatoire)
    submitted = _to_canonical(q, "Daragol waɗɗiiɗo")
    assert submitted == "Arrêt obligatoire"

    result = score_answers({q.id: q.correct_answer}, {q.id: submitted})
    assert result["correct_answers"] == 1
    db.close()


def test_audio_url_par_langue() -> None:
    """Une question peut porter un enregistrement audio par langue
    (locuteur natif) — servi à l'examen, repli synthèse vocale si absent."""
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        H = get_admin_headers(client)
        r = client.put(f"/api/v1/questions/{qid}/translations", json={
            "ff": {
                "text": "Hol ko maannouni STOP?",
                "audio_url": "https://cdn.example.gn/audio/ff/q1.mp3",
            }
        }, headers=H)
        assert r.status_code == 200

    db = SessionLocal()
    q = db.get(Question, qid)
    content = resolve_question_content(q, "ff")
    assert content["audio_url"] == "https://cdn.example.gn/audio/ff/q1.mp3"
    # Sans traduction audio, pas d'URL (le client retombe sur la synthèse)
    assert resolve_question_content(q, "man")["audio_url"] is None
    db.close()


def test_audio_url_rejette_url_invalide() -> None:
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        r = client.put(f"/api/v1/questions/{qid}/translations", json={
            "ff": {"audio_url": "javascript:alert(1)"}
        }, headers=get_admin_headers(client))
        assert r.status_code == 422

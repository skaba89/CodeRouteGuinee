"""
Test — Audio des questions en langues nationales (Pular, Malinké, Soussou…).

CHOIX DE CONCEPTION : seul l'ORAL est localisé.
Le texte affiché reste toujours en français (les langues nationales
guinéennes n'ont pas de standard d'écriture partagé). Le candidat VOIT la
question en français et l'ENTEND dans sa langue — ce qui inclut les
citoyens qui parlent ces langues sans les lire.
"""
from __future__ import annotations

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


def test_texte_reste_en_francais_quelle_que_soit_la_langue() -> None:
    """Le texte et les options ne sont JAMAIS traduits — seul l'audio l'est."""
    init_db()
    qid = _make_question()
    db = SessionLocal()
    q = db.get(Question, qid)
    for lang in ("fr", "ff", "man", "sus"):
        content = resolve_question_content(q, lang)
        assert content["text"] == "Que signifie un panneau STOP ?"
        assert content["options"][0] == "Arrêt obligatoire"
    db.close()


def test_associer_un_enregistrement_audio() -> None:
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        r = client.put(f"/api/v1/questions/{qid}/audio", json={
            "ff": "https://cdn.example.gn/audio/ff/q1.mp3",
            "man": "/audio/man/q1.mp3",
        }, headers=get_admin_headers(client))
        assert r.status_code == 200, r.text[:200]

    db = SessionLocal()
    q = db.get(Question, qid)
    # L'audio suit la langue…
    assert resolve_question_content(q, "ff")["audio_url"] == "https://cdn.example.gn/audio/ff/q1.mp3"
    assert resolve_question_content(q, "man")["audio_url"] == "/audio/man/q1.mp3"
    # …mais le texte reste français
    assert resolve_question_content(q, "ff")["text"] == "Que signifie un panneau STOP ?"
    # Langue sans enregistrement → pas d'audio (repli synthèse vocale côté client)
    assert resolve_question_content(q, "sus")["audio_url"] is None
    assert "ff" in available_languages(q)
    db.close()


def test_audio_rejette_url_malveillante() -> None:
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        r = client.put(f"/api/v1/questions/{qid}/audio",
                       json={"ff": "javascript:alert(1)"},
                       headers=get_admin_headers(client))
        assert r.status_code == 422


def test_audio_suppression() -> None:
    """Une valeur vide supprime l'enregistrement d'une langue."""
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        H = get_admin_headers(client)
        client.put(f"/api/v1/questions/{qid}/audio",
                   json={"ff": "https://cdn.example.gn/a.mp3"}, headers=H)
        r = client.put(f"/api/v1/questions/{qid}/audio", json={"ff": ""}, headers=H)
        assert r.status_code == 200

    db = SessionLocal()
    q = db.get(Question, qid)
    assert resolve_question_content(q, "ff")["audio_url"] is None
    db.close()


def test_examen_sert_l_audio_dans_la_langue() -> None:
    """L'examen expose audio_url pour la langue demandée."""
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        client.put(f"/api/v1/questions/{qid}/audio",
                   json={"ff": "https://cdn.example.gn/audio/ff/q1.mp3"},
                   headers=get_admin_headers(client))

    db = SessionLocal()
    q = db.get(Question, qid)
    content = resolve_question_content(q, "ff")
    assert content["audio_url"] is not None
    assert content["text"] == "Que signifie un panneau STOP ?"  # français
    db.close()


def test_audio_coverage_endpoint() -> None:
    """L'admin peut consulter la couverture audio par langue."""
    init_db()
    qid = _make_question()
    with TestClient(app) as client:
        H = get_admin_headers(client)
        client.put(f"/api/v1/questions/{qid}/audio",
                   json={"ff": "https://cdn.example.gn/a.mp3"}, headers=H)

        r = client.get("/api/v1/questions/audio-coverage", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["questions_total"] >= 1
        langs = {l["code"]: l for l in data["languages"]}
        assert set(langs) >= {"ff", "man", "sus"}
        assert langs["ff"]["recorded"] >= 1
        # Une langue sans enregistrement reste à 0
        assert langs["kss"]["recorded"] == 0


def test_import_audio_script_report() -> None:
    """Le script d'import expose la couverture sans rien écrire."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import import_audio

    init_db()
    _make_question()
    db = SessionLocal()
    try:
        # Ne doit pas lever
        import_audio.report_coverage(db)
    finally:
        db.close()


def test_import_audio_valide_les_urls() -> None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import import_audio

    assert import_audio._valid_url("https://cdn.gn/a.mp3") is True
    assert import_audio._valid_url("/audio/ff/1.mp3") is True
    assert import_audio._valid_url("javascript:alert(1)") is False
    assert import_audio._valid_url("http://insecure.gn/a.mp3") is False

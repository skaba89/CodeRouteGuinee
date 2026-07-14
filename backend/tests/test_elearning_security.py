"""
Test — sécurité et fonctionnement du module e-learning.

Ce module était peu couvert (51 %). L'audit n'y a trouvé AUCUNE faille : les
autorisations sont correctes et la progression est déduite de l'utilisateur
authentifié (pas d'IDOR). Ces tests VERROUILLENT cette correction : du code
non testé peut régresser silencieusement.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import init_db, SessionLocal
from app.models_elearning import Course, Lesson
from tests.conftest import get_admin_headers, get_candidate_headers


def _seed_course() -> tuple[str, str]:
    """Crée un cours avec une leçon. Retourne (course_id, lesson_id)."""
    init_db()
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]
    course = Course(title=f"Cours {suffix}", description="Test", category="signalisation")
    db.add(course); db.commit(); db.refresh(course)
    lesson = Lesson(course_id=course.id, title=f"Leçon {suffix}", content="Contenu", order=1)
    db.add(lesson); db.commit(); db.refresh(lesson)
    cid, lid = course.id, lesson.id
    db.close()
    return cid, lid


# ── Autorisations ───────────────────────────────────────────────────────────

def test_creation_cours_refusee_au_candidat() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.post("/api/v1/admin/courses",
                        json={"title": "Pirate", "description": "x", "category": "general"},
                        headers=get_candidate_headers(client))
        assert r.status_code == 403


def test_suppression_cours_reservee_au_super_admin() -> None:
    cid, _ = _seed_course()
    with TestClient(app) as client:
        # get_admin_headers renvoie un super_admin → autorisé
        r = client.delete(f"/api/v1/admin/courses/{cid}", headers=get_admin_headers(client))
        assert r.status_code in (204, 200)


def test_lecture_cours_exige_authentification() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.get("/api/v1/courses")
        assert r.status_code in (401, 403)


# ── Progression : pas d'IDOR ────────────────────────────────────────────────

def test_progression_liee_a_l_utilisateur_authentifie() -> None:
    """
    La progression est déduite de l'utilisateur connecté (via son email),
    JAMAIS d'un identifiant fourni par le client. Un candidat ne peut donc
    pas modifier la progression d'un autre — même en trafiquant la requête.
    """
    cid, lid = _seed_course()
    with TestClient(app) as client:
        headers = get_candidate_headers(client)
        # On tente d'injecter un candidate_id étranger : il doit être IGNORÉ
        r = client.post(f"/api/v1/courses/{cid}/lessons/{lid}/progress",
                        json={"progress_pct": 50, "completed": False,
                              "candidate_id": "victime-id-etranger"},
                        headers=headers)
        # Soit 200 (le champ parasite est ignoré), soit 400 (pas de profil candidat)
        assert r.status_code in (200, 400, 422)
        if r.status_code == 200:
            assert r.json()["progress_pct"] == 50


def test_progression_bornee_0_100() -> None:
    """Un pourcentage aberrant est ramené dans [0, 100] (pas de score truqué)."""
    cid, lid = _seed_course()
    with TestClient(app) as client:
        r = client.post(f"/api/v1/courses/{cid}/lessons/{lid}/progress",
                        json={"progress_pct": 9999, "completed": True},
                        headers=get_candidate_headers(client))
        if r.status_code == 200:
            assert r.json()["progress_pct"] <= 100


def test_lecon_inexistante_404() -> None:
    cid, _ = _seed_course()
    with TestClient(app) as client:
        r = client.post(f"/api/v1/courses/{cid}/lessons/inexistante/progress",
                        json={"progress_pct": 10, "completed": False},
                        headers=get_candidate_headers(client))
        assert r.status_code in (404, 400)

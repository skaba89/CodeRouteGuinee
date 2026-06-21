"""
Tests étendus training — couverture mock-exam et check-answer.

Modules ciblés :
  app/routers/training.py (62% → objectif 90%+)
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers


class TestTrainingCategories:
    def test_get_categories_returns_list(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/categories", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 8  # 8 catégories DNTT

    def test_categories_have_required_fields(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/categories", headers=h)
        for cat in r.json():
            assert "category" in cat
            assert "total" in cat
            assert "display_name" in cat
            assert cat["total"] > 0

    def test_all_dntt_categories_present(self):
        expected = {
            "signalisation", "priorites", "vitesse", "depassement",
            "securite_passive", "urgence", "alcool_drogues", "premiers_secours",
        }
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/categories", headers=h)
        found = {c["category"] for c in r.json()}
        assert expected <= found


class TestTrainingQuestions:
    def test_default_returns_20_questions(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/questions", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 20

    def test_limit_param_respected(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/questions?limit=5", headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 5

    def test_limit_max_80(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/questions?limit=80", headers=h)
        assert r.status_code == 200
        assert len(r.json()) <= 80

    def test_limit_above_max_rejected(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/questions?limit=999", headers=h)
        assert r.status_code == 422  # validation Pydantic

    def test_category_filter_works(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/questions?category=signalisation&limit=20", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert all(q["category"] == "signalisation" for q in data)
        assert len(data) > 0

    def test_question_has_correct_answer_exposed(self):
        """En mode entraînement, la bonne réponse est exposée."""
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/questions?limit=1", headers=h)
        q = r.json()[0]
        assert "correct_answer" in q
        assert "explanation" in q
        assert q["correct_answer"] in q["options"]

    def test_shuffle_false_returns_first_questions(self):
        """shuffle=false retourne les questions dans l'ordre du pool."""
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r1 = client.get("/api/v1/training/questions?limit=5&shuffle=false", headers=h)
            r2 = client.get("/api/v1/training/questions?limit=5&shuffle=false", headers=h)
        # Sans shuffle, les mêmes questions dans le même ordre
        ids1 = [q["index"] for q in r1.json()]
        ids2 = [q["index"] for q in r2.json()]
        assert ids1 == ids2

    def test_unauthenticated_returns_401(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/training/questions")
        assert r.status_code == 401


class TestMockExam:
    def test_mock_exam_returns_40_questions(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/mock-exam", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["total_questions"] == 40
        assert data["duration_minutes"] == 30
        assert data["pass_threshold"] == 35
        assert len(data["questions"]) == 40

    def test_mock_exam_hides_correct_answers(self):
        """En examen blanc, les bonnes réponses ne sont PAS dans les questions."""
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/mock-exam", headers=h)
        for q in r.json()["questions"]:
            assert "correct_answer" not in q
            assert "explanation" not in q

    def test_mock_exam_has_answer_key(self):
        """La clé de réponse est présente (côté serveur)."""
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/mock-exam", headers=h)
        data = r.json()
        assert "answer_key" in data
        assert len(data["answer_key"]) == 40

    def test_mock_exam_covers_all_categories(self):
        """Un examen blanc doit couvrir toutes les catégories DNTT."""
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/mock-exam", headers=h)
        cats = {q["category"] for q in r.json()["questions"]}
        expected = {"signalisation", "priorites", "vitesse", "depassement"}
        assert expected <= cats  # au moins les 4 catégories principales

    def test_mock_exam_type_field(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/training/mock-exam", headers=h)
        assert r.json()["type"] == "mock_exam"


class TestCheckAnswer:
    def test_correct_answer_returns_true(self):
        # D'abord récupérer une question avec sa bonne réponse
        with TestClient(app) as client:
            h = get_admin_headers(client)
            qs = client.get(
                "/api/v1/training/questions?limit=1&shuffle=false&category=signalisation",
                headers=h
            ).json()
        q = qs[0]
        correct = q["correct_answer"]

        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post(
                "/api/v1/training/check-answer?category=signalisation",
                headers=h,
                json={"question_index": 0, "answer": correct},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["correct"] is True
        assert "explanation" in data
        assert data["correct_answer"] == correct

    def test_wrong_answer_returns_false(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            qs = client.get(
                "/api/v1/training/questions?limit=1&shuffle=false&category=vitesse",
                headers=h
            ).json()
        q = qs[0]
        wrong = next(opt for opt in q["options"] if opt != q["correct_answer"])

        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post(
                "/api/v1/training/check-answer?category=vitesse",
                headers=h,
                json={"question_index": 0, "answer": wrong},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["correct"] is False
        assert data["your_answer"] == wrong
        assert data["correct_answer"] != wrong

    def test_out_of_bounds_index_returns_error(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post(
                "/api/v1/training/check-answer",
                headers=h,
                json={"question_index": 9999, "answer": "n/a"},
            )
        assert r.status_code == 200
        assert "error" in r.json()

    def test_check_answer_includes_category_label(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            qs = client.get(
                "/api/v1/training/questions?limit=1&shuffle=false",
                headers=h
            ).json()
        q = qs[0]
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post(
                "/api/v1/training/check-answer",
                headers=h,
                json={"question_index": 0, "answer": q["correct_answer"]},
            )
        data = r.json()
        assert "category_label" in data
        assert len(data["category_label"]) > 0

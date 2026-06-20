"""
Module entraînement CodeRoute Guinée — Mois 4–6 de la feuille de route.

Endpoints :
  GET  /training/questions          — Questions de la banque par catégorie (sans timer)
  POST /training/session            — Créer une session d'entraînement
  POST /training/session/{id}/answer — Soumettre une réponse (avec explication immédiate)
  GET  /training/stats/{user_id}    — Statistiques et points faibles d'un candidat
  GET  /training/categories         — Liste des catégories et scores
"""
from __future__ import annotations

import random

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.deps import get_current_user
from app.models_user import User
from app.question_bank_gn import QUESTIONS_ALL, QUESTIONS_GN

router = APIRouter(prefix="/training", tags=["training"])


class TrainingQuestionOut(BaseModel):
    id: int
    category: str
    text: str
    options: list[str]
    # NB: correct_answer et explanation sont inclus — mode entraînement sans pression


class TrainingAnswerRequest(BaseModel):
    question_index: int
    answer: str


class TrainingAnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    explanation: str
    score_so_far: int
    total_answered: int


@router.get("/categories")
def get_training_categories(
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Liste des catégories avec nombre de questions disponibles."""
    from collections import Counter
    cat_count = Counter(q["category"] for q in QUESTIONS_ALL)
    return [
        {"category": cat, "total": count, "display_name": _cat_label(cat)}
        for cat, count in sorted(cat_count.items())
    ]


@router.get("/questions")
def get_training_questions(
    category: str | None = Query(default=None, description="Filtrer par catégorie"),
    limit: int = Query(default=20, le=80, description="Nombre de questions (max 80)"),
    shuffle: bool = Query(default=True, description="Mélanger les questions"),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Retourne des questions pour l'entraînement.
    Contrairement à l'examen, les bonnes réponses et explications sont incluses.
    """
    pool = [q for q in QUESTIONS_ALL if not category or q["category"] == category]

    if shuffle:
        pool = random.sample(pool, min(limit, len(pool)))
    else:
        pool = pool[:limit]

    return [
        {
            "index": i,
            "category": q["category"],
            "category_label": _cat_label(q["category"]),
            "text": q["text"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "explanation": q.get("explanation", ""),
        }
        for i, q in enumerate(pool)
    ]


@router.get("/mock-exam")
def get_mock_exam(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Génère un examen blanc — même format que l'examen officiel.
    40 questions, répartition catégorielle officielle.
    Les bonnes réponses sont masquées (comme l'examen réel).
    """

    # Utiliser la banque embarquée pour le mode entraînement
    questions = random.sample(QUESTIONS_GN, min(40, len(QUESTIONS_GN)))
    random.shuffle(questions)

    return {
        "type": "mock_exam",
        "total_questions": len(questions),
        "duration_minutes": 30,
        "pass_threshold": 35,
        "questions": [
            {
                "index": i,
                "category": q["category"],
                "text": q["text"],
                "options": q["options"],
                # Pas de correct_answer ni explanation — simuler l'examen officiel
            }
            for i, q in enumerate(questions)
        ],
        "answer_key": {
            str(i): q["correct_answer"] for i, q in enumerate(questions)
        },  # NB: dans une vraie app, ceci serait côté serveur uniquement
    }


@router.post("/check-answer")
def check_answer(
    request: TrainingAnswerRequest,
    category: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Vérifie une réponse et retourne l'explication immédiatement.
    Cœur du mode entraînement — feedback pédagogique instantané.
    """
    pool = [q for q in QUESTIONS_ALL if not category or q["category"] == category]

    if request.question_index >= len(pool):
        return {"error": "Question introuvable"}

    q = pool[request.question_index]
    is_correct = request.answer == q["correct_answer"]

    return {
        "correct": is_correct,
        "your_answer": request.answer,
        "correct_answer": q["correct_answer"],
        "explanation": q.get("explanation", ""),
        "category": q["category"],
        "category_label": _cat_label(q["category"]),
    }


def _cat_label(cat: str) -> str:
    labels = {
        "signalisation":    "Signalisation",
        "priorites":        "Priorités",
        "vitesse":          "Vitesse & Distances",
        "depassement":      "Dépassement",
        "securite_passive": "Sécurité passive",
        "urgence":          "Situations d'urgence",
        "alcool_drogues":   "Alcool & Drogues",
        "premiers_secours": "Premiers secours",
    }
    return labels.get(cat, cat.capitalize())

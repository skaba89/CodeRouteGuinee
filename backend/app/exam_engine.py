"""
Moteur d'examen CodeRoute Guinée — Catégorie B.

Configuration institutionnelle actuellement utilisée par la plateforme :
  - 40 questions tirées aléatoirement par catégorie
  - Seuil d'admission : 35 bonnes réponses sur 40 (87,5 %)
  - Durée maximale : 30 minutes
  - 1 seul passage autorisé par session
  - Résultat traçable : hash SHA-256 de la banque enregistré à la création

IMPORTANT : ces paramètres restent configurables tant que leur validation
formelle par l'autorité DNTT n'est pas matérialisée dans le référentiel projet.
"""
from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from typing import TYPE_CHECKING

from app.question_bank_gn import QUESTIONS_TRAINING_FULL

if TYPE_CHECKING:
    from app.models_question import Question

# ── Paramètres institutionnels courants ────────────────────────────────────

EXAM_QUESTIONS_TOTAL = 40
EXAM_PASS_THRESHOLD = 35
EXAM_DURATION_MINUTES = 30

CATEGORY_DISTRIBUTION: dict[str, int] = {
    "signalisation": 10,
    "priorites": 6,
    "vitesse": 5,
    "depassement": 5,
    "securite_passive": 4,
    "urgence": 4,
    "alcool_drogues": 3,
    "premiers_secours": 3,
}

assert sum(CATEGORY_DISTRIBUTION.values()) == EXAM_QUESTIONS_TOTAL, (
    f"La répartition catégorielle doit totaliser {EXAM_QUESTIONS_TOTAL} questions"
)


# ── Isolation de la banque d'entraînement historique ──────────────────────

def _question_text_key(value: str) -> str:
    return " ".join((value or "").strip().casefold().split())


# Le seed historique a marqué les 160 questions d'entraînement comme
# `approved`. Une base déjà créée peut donc encore contenir ce mauvais statut.
# On exclut explicitement ces entrées connues du pool officiel, sans empêcher
# de futures questions officiellement importées et approuvées d'être utilisées.
_LEGACY_TRAINING_TEXT_KEYS = frozenset(
    _question_text_key(str(item.get("text", "")))
    for item in QUESTIONS_TRAINING_FULL
    if item.get("text")
)


def filter_official_exam_pool(questions: list[Question]) -> list[Question]:
    """Retire du pool les questions du dataset d'entraînement historique.

    Le workflow officiel reste gouverné par `validation_status=approved` dans
    le routeur. Ce filtre est un garde de compatibilité pour les bases seedées
    avant la séparation stricte des deux banques.
    """
    return [
        question
        for question in questions
        if _question_text_key(getattr(question, "text", "")) not in _LEGACY_TRAINING_TEXT_KEYS
    ]


# ── Sélection aléatoire ────────────────────────────────────────────────────

def select_exam_questions(
    questions: list[Question],
    seed: str | None = None,
) -> list[Question]:
    """Sélectionne les questions selon la répartition configurée.

    Les 160 questions du dataset d'entraînement historique sont toujours
    exclues avant sélection, même si une ancienne base les a marquées
    `approved` par erreur.

    Si une catégorie ne contient pas assez de questions, le manque est
    complété avec les autres catégories. Le routeur officiel contrôle ensuite
    que le résultat contient exactement `EXAM_QUESTIONS_TOTAL` questions et
    refuse le démarrage dans le cas contraire.
    """
    questions = filter_official_exam_pool(questions)
    rng = random.Random(seed)

    by_cat: dict[str, list[Question]] = defaultdict(list)
    for q in questions:
        by_cat[q.category].append(q)

    selected: list[Question] = []
    shortfall = 0

    for cat, count in CATEGORY_DISTRIBUTION.items():
        pool = by_cat.get(cat, [])
        if len(pool) >= count:
            selected.extend(rng.sample(pool, count))
        else:
            selected.extend(pool)
            shortfall += count - len(pool)

    if shortfall > 0:
        already_selected_ids = {q.id for q in selected}
        remaining = [q for q in questions if q.id not in already_selected_ids]
        supplement = rng.sample(remaining, min(shortfall, len(remaining)))
        selected.extend(supplement)

    rng.shuffle(selected)
    return selected[:EXAM_QUESTIONS_TOTAL]


# ── Hachage de la banque ──────────────────────────────────────────────────

def build_question_bank_hash(questions: list[Question]) -> str:
    """Hash SHA-256 déterministe du pool officiel réellement éligible."""
    official_questions = filter_official_exam_pool(questions)
    payload = "|".join(
        f"{q.id}:{q.correct_answer}:{q.is_active}"
        for q in sorted(official_questions, key=lambda q: q.id)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_selected_questions_hash(questions: list[Question]) -> str:
    """Hash SHA-256 des questions sélectionnées pour cet examen précis."""
    payload = "|".join(
        f"{q.id}:{q.correct_answer}"
        for q in questions
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Notation ──────────────────────────────────────────────────────────────

def score_answers(
    answer_key: dict[str, str],
    submitted_answers: dict[str, str],
) -> dict:
    """Calcule le score de l'examen à partir de la clé serveur."""
    total = len(answer_key)
    correct = 0
    wrong = 0
    unanswered = 0

    for question_id, expected in answer_key.items():
        submitted = submitted_answers.get(question_id)
        if submitted is None:
            unanswered += 1
        elif submitted == expected:
            correct += 1
        else:
            wrong += 1

    score_percent = round((correct / total) * 100, 2) if total else 0

    if total == EXAM_QUESTIONS_TOTAL:
        passed = correct >= EXAM_PASS_THRESHOLD
    else:
        passed = score_percent >= (EXAM_PASS_THRESHOLD / EXAM_QUESTIONS_TOTAL * 100)

    return {
        "total_questions": total,
        "correct_answers": correct,
        "wrong_answers": wrong,
        "unanswered": unanswered,
        "score_percent": score_percent,
        "passed": passed,
        "threshold": EXAM_PASS_THRESHOLD,
    }


# ── Résumé lisible ─────────────────────────────────────────────────────────

def build_score_summary(result: dict, candidate_name: str = "") -> str:
    """Génère un résumé textuel du résultat pour les logs et l'audit."""
    verdict = "ADMIS" if result["passed"] else "AJOURNÉ"
    name = f" — {candidate_name}" if candidate_name else ""
    return (
        f"{verdict}{name} : {result['correct_answers']}/{result['total_questions']} "
        f"({result['score_percent']}%) "
        f"[seuil {result['threshold']}/{result['total_questions']}]"
    )

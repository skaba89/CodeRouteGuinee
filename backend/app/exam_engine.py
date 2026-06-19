"""
Moteur d'examen CodeRoute Guinée — Catégorie B.

Règles officielles DNTT / Ministère des Transports :
  - 40 questions obligatoires tirées aléatoirement par catégorie
  - Seuil d'admission : 35 bonnes réponses sur 40 (87,5 %)
  - Durée maximale : 30 minutes
  - 1 seul passage autorisé par session
  - Résultat infalsifiable : hash SHA-256 de la banque enregistré à la création
"""
from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models_question import Question

# ── Constantes officielles ─────────────────────────────────────────────────

EXAM_QUESTIONS_TOTAL = 40        # Nombre de questions par examen
EXAM_PASS_THRESHOLD = 35         # Minimum pour être admis (35/40 = 87,5 %)
EXAM_DURATION_MINUTES = 30       # Durée maximale

# Répartition officielle par catégorie (total = 40)
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


# ── Sélection aléatoire ────────────────────────────────────────────────────

def select_exam_questions(
    questions: list[Question],
    seed: str | None = None,
) -> list[Question]:
    """
    Sélectionne 40 questions selon la répartition officielle par catégorie.

    Si la banque n'a pas assez de questions dans une catégorie, toutes les
    questions disponibles dans cette catégorie sont utilisées et le reste
    est complété par les autres catégories pour maintenir le total à 40.

    Args:
        questions: liste complète des questions actives de la banque
        seed: graine pour la reproductibilité (None = aléatoire)

    Returns:
        Liste de 40 questions mélangées dans un ordre aléatoire
    """
    rng = random.Random(seed)

    # Grouper par catégorie
    by_cat: dict[str, list[Question]] = defaultdict(list)
    for q in questions:
        by_cat[q.category].append(q)

    selected: list[Question] = []
    shortfall = 0  # Questions manquantes dans les catégories courtes

    # Premier passage : sélection selon la distribution officielle
    for cat, count in CATEGORY_DISTRIBUTION.items():
        pool = by_cat.get(cat, [])
        if len(pool) >= count:
            selected.extend(rng.sample(pool, count))
        else:
            selected.extend(pool)  # Prendre tout si insuffisant
            shortfall += count - len(pool)

    # Deuxième passage : combler le manque avec les questions restantes
    if shortfall > 0:
        already_selected_ids = {q.id for q in selected}
        remaining = [q for q in questions if q.id not in already_selected_ids]
        supplement = rng.sample(remaining, min(shortfall, len(remaining)))
        selected.extend(supplement)

    # Mélanger l'ordre final
    rng.shuffle(selected)
    return selected[:EXAM_QUESTIONS_TOTAL]


# ── Hachage de la banque ──────────────────────────────────────────────────

def build_question_bank_hash(questions: list[Question]) -> str:
    """
    Hash SHA-256 déterministe de la banque de questions active.
    Enregistré dans ExamQuestionTrace pour garantir l'intégrité du résultat.
    """
    payload = "|".join(
        f"{q.id}:{q.correct_answer}:{q.is_active}"
        for q in sorted(questions, key=lambda q: q.id)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_selected_questions_hash(questions: list[Question]) -> str:
    """
    Hash SHA-256 des questions sélectionnées pour cet examen précis.
    Permet de vérifier a posteriori qu'aucune substitution n'a eu lieu.
    """
    payload = "|".join(
        f"{q.id}:{q.correct_answer}"
        for q in questions  # Ordre de sélection conservé
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Notation ──────────────────────────────────────────────────────────────

def score_answers(
    answer_key: dict[str, str],
    submitted_answers: dict[str, str],
) -> dict:
    """
    Calcule le score d'un examen.

    Args:
        answer_key: {question_id: correct_answer}
        submitted_answers: {question_id: submitted_answer}

    Returns:
        dict avec total_questions, correct_answers, wrong_answers,
        unanswered, score_percent, passed
    """
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

    # Règle officielle : 35/40 pour être admis
    if total == EXAM_QUESTIONS_TOTAL:
        passed = correct >= EXAM_PASS_THRESHOLD
    else:
        # Proportionnel pour les banques non standard (tests)
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

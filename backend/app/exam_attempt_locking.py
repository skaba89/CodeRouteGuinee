"""Primitives de concurrence pour les tentatives d'examen officielles.

En production PostgreSQL, les opérations sensibles doivent verrouiller la ligne
métier avant de décider de créer/finaliser une tentative. Cela évite qu'un
double clic, un retry réseau ou deux postes de centre traitent le même état en
parallèle.

SQLite ignore essentiellement ``FOR UPDATE`` ; les tests restent donc
compatibles tout en conservant le comportement de sérialisation en production.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_exam_attempt import ExamAttempt

RECOVERABLE_ATTEMPT_STATUSES = ("started", "expired")


def lock_exam_attempt(db: Session, attempt_id: str) -> ExamAttempt | None:
    """Charge une tentative avec verrou d'écriture transactionnel."""
    return db.scalar(
        select(ExamAttempt)
        .where(ExamAttempt.id == attempt_id)
        .with_for_update()
    )


def find_latest_attempt(
    db: Session,
    candidate_id: str,
    session_id: str,
) -> ExamAttempt | None:
    """Verrouille la tentative la plus récente d'un candidat pour une session.

    Cette requête sert de garde « réservation déjà consommée ». Si la dernière
    tentative est récupérable, le caller la reprend ; sinon il doit refuser un
    nouveau démarrage et passer par le workflow institutionnel de rattrapage.
    """
    return db.scalar(
        select(ExamAttempt)
        .where(
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.session_id == session_id,
        )
        .order_by(ExamAttempt.started_at.desc())
        .limit(1)
        .with_for_update()
    )


def find_recoverable_attempt(
    db: Session,
    candidate_id: str,
    session_id: str,
) -> ExamAttempt | None:
    """Retourne la tentative active/récupérable la plus récente, verrouillée.

    Une réservation ne doit jamais produire une deuxième tentative simplement
    parce que le navigateur a été rechargé ou le poste remplacé. Le verrou
    sérialise aussi deux démarrages concurrents sur PostgreSQL lorsqu'il est
    utilisé après le verrou de la réservation.
    """
    return db.scalar(
        select(ExamAttempt)
        .where(
            ExamAttempt.candidate_id == candidate_id,
            ExamAttempt.session_id == session_id,
            ExamAttempt.status.in_(RECOVERABLE_ATTEMPT_STATUSES),
        )
        .order_by(ExamAttempt.started_at.desc())
        .limit(1)
        .with_for_update()
    )

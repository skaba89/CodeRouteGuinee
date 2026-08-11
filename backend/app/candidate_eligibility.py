"""Règles d'éligibilité du parcours candidat.

Ces gardes expriment des invariants applicatifs de sécurité et de cohérence.
Ils restent configurables/ajustables avec la procédure institutionnelle finale :
le code ne les présente pas comme une homologation DNTT acquise.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.models_candidate import Candidate


def _normalized_status(candidate: Candidate) -> str:
    return (candidate.status or "registered").strip().lower()


def assert_candidate_not_suspended(candidate: Candidate, *, action: str) -> None:
    """Empêche un dossier suspendu de poursuivre une action engageante."""
    if _normalized_status(candidate) != "suspended":
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "CANDIDATE_SUSPENDED",
            "message": "Ce dossier candidat est suspendu. L'action demandée est bloquée jusqu'à régularisation.",
            "candidate_id": candidate.id,
            "candidate_reference": candidate.reference,
            "action": action,
        },
    )


def assert_candidate_can_book(candidate: Candidate) -> None:
    assert_candidate_not_suspended(candidate, action="booking")


def assert_candidate_can_pay(candidate: Candidate) -> None:
    assert_candidate_not_suspended(candidate, action="payment")


def assert_candidate_ready_for_official_exam(candidate: Candidate) -> None:
    """Exige un dossier non suspendu et une identité validée avant l'examen."""
    assert_candidate_not_suspended(candidate, action="official_exam")
    if _normalized_status(candidate) == "verified":
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "IDENTITY_VERIFICATION_REQUIRED",
            "message": "L'identité du candidat doit être vérifiée avant le contrôle d'entrée et l'examen officiel.",
            "candidate_id": candidate.id,
            "candidate_reference": candidate.reference,
            "candidate_status": _normalized_status(candidate),
        },
    )

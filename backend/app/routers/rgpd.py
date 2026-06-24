"""
Endpoints RGPD — Loi L/2022/018/AN Guinée
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_user import User
from app.rgpd import anonymize_candidate, export_candidate_data

router = APIRouter(prefix="/rgpd", tags=["rgpd"])


@router.get("/export")
def export_my_data(
    fmt: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "admin", "super_admin")),
) -> Response:
    """
    Exporte toutes les données personnelles du candidat connecté.
    Droit d'accès + portabilité — Art. 18 & 24 Loi L/2022/018/AN.
    Format : ?fmt=json (défaut) ou ?fmt=csv
    """
    from sqlalchemy import select

    from app.models_candidate import Candidate

    # Résoudre le candidat par email
    cand = db.scalar(
        select(Candidate).where(Candidate.email == current_user.email)
    )
    if not cand:
        # Admin peut exporter n'importe quel candidat via query param
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun profil candidat associé à ce compte",
        )

    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="Format invalide : json ou csv")

    data = export_candidate_data(str(cand.id), db, fmt)

    if fmt == "csv":
        return Response(
            content=data,
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f"attachment; filename=donnees_{cand.reference}.csv"},
        )
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=donnees_{cand.reference}.json"},
    )


@router.post("/delete")
def request_erasure(
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "admin", "super_admin")),
) -> dict:
    """
    Demande d'effacement des données personnelles.
    Droit à l'effacement — Art. 20 Loi L/2022/018/AN.
    Anonymise les PII en conservant les données d'examen (obligation DNTT).
    """
    from sqlalchemy import select

    from app.models_candidate import Candidate

    cand = db.scalar(
        select(Candidate).where(Candidate.email == current_user.email)
    )
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun profil candidat associé à ce compte",
        )

    payload = payload or {}
    reason = payload.get("reason", "Demande d'effacement candidat")
    result = anonymize_candidate(str(cand.id), db, reason)
    return {
        **result,
        "message": (
            "Vos données personnelles ont été anonymisées conformément à "
            "l'art. 20 de la Loi L/2022/018/AN. Vos résultats d'examens "
            "sont conservés pour obligation légale DNTT."
        ),
    }


@router.get("/export/{candidate_id}")
def admin_export_candidate(
    candidate_id: str,
    fmt: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Response:
    """Export admin des données d'un candidat spécifique."""
    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="Format invalide")

    try:
        data = export_candidate_data(candidate_id, db, fmt)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    media_type = "text/csv; charset=utf-8-sig" if fmt == "csv" else "application/json"
    return Response(content=data, media_type=media_type)


@router.post("/delete/{candidate_id}")
def admin_anonymize_candidate(
    candidate_id: str,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    """Anonymisation admin d'un candidat (super_admin uniquement)."""
    payload = payload or {}
    reason = payload.get("reason", f"Anonymisation admin par {current_user.email}")
    try:
        return anonymize_candidate(candidate_id, db, reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

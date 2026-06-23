"""
Endpoints tarifs — CodeRoute Guinée
GET  /api/v1/tarifs/current         — tarifs actuels (public)
GET  /api/v1/admin/tarifs           — liste complète (admin)
PUT  /api/v1/admin/tarifs/{cle}     — mettre à jour un tarif (super_admin)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_user import User
from app.tarifs import DEFAULT_TARIFS, get_all_tarifs, update_tarif

router_public = APIRouter(prefix="/tarifs", tags=["tarifs"])
router_admin  = APIRouter(prefix="/admin/tarifs", tags=["admin-tarifs"])


# ── Public ────────────────────────────────────────────────────────────────────

@router_public.get("/current")
def get_current_tarifs(db: Session = Depends(get_db)) -> dict:
    """
    Retourne les tarifs en vigueur (lecture seule, sans auth).
    Utilisé par le frontend pour afficher les prix à jour.
    """
    try:
        tarifs = get_all_tarifs(db)
        actifs = [t for t in tarifs if t["actif"]]
    except Exception:
        # Fallback sur les défauts si la table n'existe pas encore
        actifs = [
            {"cle": k, "libelle": v["libelle"], "montant_gnf": v["montant_gnf"],
             "categorie_permis": v["categorie_permis"], "actif": True}
            for k, v in DEFAULT_TARIFS.items()
        ]
    return {"tarifs": actifs, "currency": "GNF"}


# ── Admin ─────────────────────────────────────────────────────────────────────

@router_admin.get("")
def list_tarifs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """Liste tous les tarifs (actifs + inactifs)."""
    tarifs = get_all_tarifs(db)
    return {"tarifs": tarifs, "currency": "GNF"}


@router_admin.put("/{cle}")
def update_tarif_endpoint(
    cle: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    """
    Modifier le montant d'un tarif (super_admin uniquement).
    Payload : { "montant_gnf": 150000 }
    """
    montant = payload.get("montant_gnf")
    if not isinstance(montant, int) or montant <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="montant_gnf doit être un entier positif",
        )
    try:
        result = update_tarif(cle, montant, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return result

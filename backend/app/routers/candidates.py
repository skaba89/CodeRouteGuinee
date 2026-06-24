import csv
import io
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_user import User
from app.schemas import CandidateCreate, CandidateOfficialImportRequest, CandidateOfficialImportResult, CandidateRead

router = APIRouter(prefix="/candidates", tags=["candidates"])


def build_candidate_reference(db: Session) -> str:
    count = (db.scalar(select(func.count(Candidate.id))) or 0) + 1
    return f"GN-CODE-{datetime.now(UTC).year}-{count:06d}"


@router.get("", response_model=dict)
def list_candidates(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> list[Candidate]:
    q = select(Candidate).order_by(Candidate.created_at.desc())
    if search:
        term = f"%{search.strip()}%"
        q = q.where(
            or_(
                Candidate.first_name.ilike(term),
                Candidate.last_name.ilike(term),
                Candidate.identity_number.ilike(term),
                Candidate.reference.ilike(term),
            )
        )
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    raw_items = list(db.scalars(q.offset(offset).limit(limit)).all())
    items = [CandidateRead.model_validate(x) for x in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.get("/me", response_model=CandidateRead | None)
def get_my_candidate_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "admin", "super_admin")),
) -> Candidate | None:
    """
    Retourne le profil candidat associé à l'email de l'utilisateur connecté.
    Utilisé par les candidats pour accéder à leurs propres données.
    """
    candidate = db.scalar(
        select(Candidate).where(Candidate.email == current_user.email)
    )
    if not candidate:
        # Essayer par numéro d'identité si l'email est dans le champ phone
        # (certains candidats enregistrés avant l'ajout du champ email)
        return None
    return candidate


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Candidate:
    candidate = Candidate(reference=build_candidate_reference(db), **payload.model_dump())
    db.add(candidate)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="candidate.created",
            entity="candidate",
            entity_id=candidate.id,
            details={"reference": candidate.reference, "identity_number": candidate.identity_number},
        )
    )
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/export.csv", tags=["candidates"])
def export_candidates_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
    status_filter: str | None = Query(default=None, alias="status"),
    permit_category: str | None = Query(default=None),
    city: str | None = Query(default=None),
) -> Response:
    """
    Export CSV de tous les candidats pour le reporting DNTT.
    Filtres optionnels : status, permit_category, city.
    """
    from sqlalchemy import select as _select
    query = _select(Candidate)
    if status_filter:
        query = query.where(Candidate.status == status_filter)
    if permit_category:
        query = query.where(Candidate.permit_category == permit_category)
    if city:
        query = query.where(Candidate.city == city) if hasattr(Candidate, 'city') else query

    # Limite de sécurité pour éviter les OOM avec de gros volumes
    MAX_EXPORT_ROWS = 5_000
    total_rows = db.scalar(__import__("sqlalchemy").select(__import__("sqlalchemy").func.count()).select_from(query.subquery())) or 0
    candidates = db.scalars(
        query.order_by(Candidate.last_name, Candidate.first_name).limit(MAX_EXPORT_ROWS)
    ).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "reference", "nom", "prenom", "numero_identite",
        "telephone", "email", "categorie_permis", "statut", "date_inscription",
    ])
    for cand in candidates:
        writer.writerow([
            cand.reference,
            cand.last_name,
            cand.first_name,
            cand.identity_number,
            cand.phone,
            getattr(cand, "email", "") or "",
            cand.permit_category,
            cand.status,
            cand.created_at.strftime("%Y-%m-%d") if cand.created_at else "",
        ])

    content = output.getvalue()
    headers = {
        "Content-Disposition": "attachment; filename=candidats_coderoute.csv",
        "X-Total-Count":   str(total_rows),
        "X-Exported-Count": str(len(candidates)),
        "X-Max-Rows":       str(MAX_EXPORT_ROWS),
    }
    if total_rows > MAX_EXPORT_ROWS:
        headers["X-Truncated"] = "true"
    return Response(
        content=content.encode("utf-8-sig"),   # BOM pour Excel
        media_type="text/csv; charset=utf-8-sig",
        headers=headers,
    )


@router.post("/import-official", response_model=CandidateOfficialImportResult)
def import_official_candidates(
    payload: CandidateOfficialImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CandidateOfficialImportResult:
    normalized_identities = [row.identity_number.strip().upper() for row in payload.candidates]
    duplicate_identities = sorted({identity for identity in normalized_identities if normalized_identities.count(identity) > 1})
    if duplicate_identities:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Duplicate candidate identities in import payload", "identity_numbers": duplicate_identities},
        )

    existing_candidates = {
        candidate.identity_number.upper(): candidate
        for candidate in db.scalars(select(Candidate).where(Candidate.identity_number.in_(normalized_identities))).all()
    }
    if payload.dry_run:
        existing_ids = [identity for identity in normalized_identities if identity in existing_candidates]
        return CandidateOfficialImportResult(
            dry_run=True,
            imported=len(normalized_identities),
            created=len(normalized_identities) - len(existing_ids),
            updated=len(existing_ids),
            skipped=0,
            candidate_ids=[existing_candidates[identity].id for identity in existing_ids],
            references=[existing_candidates[identity].reference for identity in existing_ids],
        )

    created = 0
    updated = 0
    candidate_ids: list[str] = []
    references: list[str] = []

    for row in payload.candidates:
        identity_number = row.identity_number.strip().upper()
        candidate = existing_candidates.get(identity_number)
        if candidate is None:
            candidate = Candidate(reference=build_candidate_reference(db), identity_number=identity_number)
            created += 1
        else:
            updated += 1
        candidate.first_name = row.first_name.strip()
        candidate.last_name = row.last_name.strip()
        candidate.identity_number = identity_number
        candidate.phone = row.phone.strip()
        candidate.permit_category = row.permit_category.strip().upper()
        candidate.status = row.status
        db.add(candidate)
        db.flush()
        candidate_ids.append(candidate.id)
        references.append(candidate.reference)

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="candidate.official_import",
            entity="candidate",
            entity_id="official-import",
            details={
                "source": payload.source,
                "reason": payload.reason,
                "imported": len(candidate_ids),
                "created": created,
                "updated": updated,
                "references": references[:50],
            },
        )
    )
    db.commit()
    return CandidateOfficialImportResult(
        dry_run=False,
        imported=len(candidate_ids),
        created=created,
        updated=updated,
        skipped=0,
        candidate_ids=candidate_ids,
        references=references,
    )

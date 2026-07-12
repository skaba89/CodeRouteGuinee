from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_question import Question
from app.models_user import User
from app.schemas import QuestionCreate, QuestionMediaUpdate, QuestionRejectionRequest, QuestionOfficialImportRequest, QuestionOfficialImportResult, QuestionRead

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=dict)
def list_questions(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> list[Question]:
    q = select(Question).order_by(Question.category.asc(), Question.created_at.desc())
    if is_active is not None:
        q = q.where(Question.is_active.is_(is_active))
    if category:
        q = q.where(Question.category == category)
    if search:
        term = f"%{search.strip()}%"
        q = q.where(Question.text.ilike(term))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    raw_items = list(db.scalars(q.offset(offset).limit(limit)).all())
    items = [QuestionRead.model_validate(x) for x in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin", "super_admin"))])
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)) -> Question:
    question = Question(**payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def _question_key(category: str, text: str) -> tuple[str, str]:
    return category.strip().lower(), " ".join(text.strip().lower().split())


@router.post("/import-official", response_model=QuestionOfficialImportResult)
def import_official_questions(
    payload: QuestionOfficialImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> QuestionOfficialImportResult:
    seen_keys: set[tuple[str, str]] = set()
    duplicate_texts: list[str] = []
    for row in payload.questions:
        key = _question_key(row.category, row.text)
        if key in seen_keys:
            duplicate_texts.append(row.text[:80])
        seen_keys.add(key)
        if row.correct_answer not in row.options:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Correct answer must be present in options", "question": row.text[:80]},
            )
    if duplicate_texts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Duplicate questions in import payload", "questions": duplicate_texts},
        )

    existing_questions = db.scalars(select(Question)).all()
    existing_by_key = {_question_key(question.category, question.text): question for question in existing_questions}
    ordered_keys = [_question_key(row.category, row.text) for row in payload.questions]
    if payload.dry_run:
        existing_keys = [key for key in ordered_keys if key in existing_by_key]
        return QuestionOfficialImportResult(
            dry_run=True,
            imported=len(ordered_keys),
            created=len(ordered_keys) - len(existing_keys),
            updated=len(existing_keys),
            skipped=0,
            question_ids=[existing_by_key[key].id for key in existing_keys],
        )

    created = 0
    updated = 0
    question_ids: list[str] = []

    for row in payload.questions:
        key = _question_key(row.category, row.text)
        question = existing_by_key.get(key)
        if question is None:
            question = Question(category=row.category.strip(), text=row.text.strip())
            created += 1
        else:
            updated += 1
        question.category = row.category.strip()
        question.text = row.text.strip()
        question.options = [option.strip() for option in row.options]
        question.correct_answer = row.correct_answer.strip()
        question.explanation = row.explanation.strip() if row.explanation else None
        question.media_type = row.media_type
        question.media_url = row.media_url.strip() if row.media_url else None
        question.media_alt = row.media_alt.strip() if row.media_alt else None
        question.is_active = row.is_active
        db.add(question)
        db.flush()
        question_ids.append(question.id)

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="question.official_import",
            entity="question",
            entity_id="official-import",
            details={
                "source": payload.source,
                "reason": payload.reason,
                "imported": len(question_ids),
                "created": created,
                "updated": updated,
                "question_ids": question_ids[:50],
            },
        )
    )
    db.commit()
    return QuestionOfficialImportResult(
        dry_run=False,
        imported=len(question_ids),
        created=created,
        updated=updated,
        skipped=0,
        question_ids=question_ids,
    )


@router.patch("/{question_id}/media", response_model=QuestionRead,
              dependencies=[Depends(require_roles("admin", "super_admin"))])
def update_question_media(
    question_id: str,
    payload: QuestionMediaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Question:
    """
    Associe un média (image/vidéo réelle, hébergée sur une URL) à une question,
    ou l'efface (media_url=None) pour revenir au visuel SVG par défaut.

    N'altère JAMAIS le texte, les options ni la réponse : uniquement le média.
    """
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")

    if payload.media_url is None:
        # Effacement : retour au visuel SVG calculé automatiquement
        question.media_type = None
        question.media_url = None
        question.media_alt = None
    else:
        question.media_type = payload.media_type or "image"
        question.media_url = payload.media_url
        question.media_alt = (payload.media_alt or "").strip() or None

    db.add(AuditLog(
        actor_id=current_user.id,
        action="question.media_updated",
        entity="question",
        entity_id=question.id,
        details={
            "media_type": question.media_type,
            "has_media": question.media_url is not None,
        },
    ))
    db.commit()
    db.refresh(question)
    return question


@router.post("/media/sign-upload",
             dependencies=[Depends(require_roles("admin", "super_admin"))])
def sign_media_upload(
    resource_type: str = "image",
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """
    Génère une signature d'upload Cloudinary pour que l'admin téléverse
    une photo ou vidéo directement depuis le navigateur (les fichiers ne
    transitent pas par le serveur).

    Renvoie 503 si Cloudinary n'est pas configuré (clés absentes).
    """
    from app.cloudinary_service import build_upload_signature, is_configured

    if resource_type not in ("image", "video"):
        raise HTTPException(status_code=422, detail="resource_type doit être 'image' ou 'video'")

    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="L'hébergement de médias (Cloudinary) n'est pas configuré. "
                   "Renseignez CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET dans les variables d'environnement.",
        )

    return build_upload_signature(resource_type)


# ── Workflow de validation officielle des questions (certification DNTT) ─────

@router.post("/{question_id}/submit-validation", response_model=QuestionRead,
             dependencies=[Depends(require_roles("admin", "super_admin"))])
def submit_question_for_validation(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Question:
    """Soumet une question à la validation DNTT (draft/rejected → submitted)."""
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")
    if question.validation_status == "approved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Question déjà approuvée.")
    question.validation_status = "submitted"
    question.rejection_reason = None
    db.add(AuditLog(actor_id=current_user.id, action="question.submitted_validation",
                    entity="question", entity_id=question.id, details={}))
    db.commit()
    db.refresh(question)
    return question


@router.post("/{question_id}/approve", response_model=QuestionRead,
             dependencies=[Depends(require_roles("super_admin"))])
def approve_question(
    question_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> Question:
    """
    Valide officiellement une question (super_admin uniquement — autorité DNTT).
    Seules les questions approuvées sont tirées à l'examen réel.
    """
    from datetime import UTC, datetime
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")
    question.validation_status = "approved"
    question.validated_by = current_user.id
    question.validated_at = datetime.now(UTC).replace(tzinfo=None)
    question.rejection_reason = None
    db.add(AuditLog(actor_id=current_user.id, action="question.approved",
                    entity="question", entity_id=question.id,
                    details={"version": question.version}))
    db.commit()
    db.refresh(question)
    return question


@router.post("/{question_id}/reject", response_model=QuestionRead,
             dependencies=[Depends(require_roles("super_admin"))])
def reject_question(
    question_id: str,
    payload: QuestionRejectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> Question:
    """Refuse une question avec motif (super_admin — autorité DNTT)."""
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")
    question.validation_status = "rejected"
    question.rejection_reason = payload.reason.strip()
    question.validated_by = current_user.id
    db.add(AuditLog(actor_id=current_user.id, action="question.rejected",
                    entity="question", entity_id=question.id,
                    details={"reason": payload.reason.strip()}))
    db.commit()
    db.refresh(question)
    return question


@router.get("/validation-summary",
            dependencies=[Depends(require_roles("admin", "super_admin"))])
def question_validation_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """Synthèse de l'état de validation de la banque de questions."""
    from sqlalchemy import func
    rows = db.execute(
        select(Question.validation_status, func.count())
        .group_by(Question.validation_status)
    ).all()
    by_status = {status_name: count for status_name, count in rows}
    total = sum(by_status.values())
    approved = by_status.get("approved", 0)
    from app.exam_engine import EXAM_QUESTIONS_TOTAL, CATEGORY_DISTRIBUTION

    # Couverture par catégorie parmi les questions approuvées
    cat_rows = db.execute(
        select(Question.category, func.count())
        .where(Question.validation_status == "approved", Question.is_active.is_(True))
        .group_by(Question.category)
    ).all()
    approved_by_cat = {cat: count for cat, count in cat_rows}
    coverage = {
        cat: {"required": required, "approved": approved_by_cat.get(cat, 0),
              "sufficient": approved_by_cat.get(cat, 0) >= required}
        for cat, required in CATEGORY_DISTRIBUTION.items()
    }
    exam_ready = all(c["sufficient"] for c in coverage.values())

    return {
        "total": total,
        "by_status": by_status,
        "approved": approved,
        "exam_questions_required": EXAM_QUESTIONS_TOTAL,
        "category_coverage": coverage,
        "exam_ready": exam_ready,
    }


@router.put("/{question_id}/audio", response_model=QuestionRead,
            dependencies=[Depends(require_roles("admin", "super_admin"))])
def set_question_audio(
    question_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Question:
    """
    Associe à une question ses enregistrements audio par langue nationale.

    Corps : {"ff": "https://…/q01_pular.mp3", "man": "/audio/man/q01.mp3", …}

    CHOIX DE CONCEPTION — seul l'ORAL est localisé :
    le texte affiché reste toujours en français (les langues nationales
    guinéennes n'ont pas de standard d'écriture largement partagé, et un
    texte écrit y introduirait une ambiguïté juridique). Le candidat VOIT la
    question en français et l'ENTEND dans sa langue.

    Sécurité : seules les URL https:// ou les chemins /audio/… sont acceptés.
    Passer une valeur vide pour une langue supprime son enregistrement.
    """
    from app.question_i18n import SUPPORTED_LANGUAGES

    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")

    cleaned: dict = dict(question.translations or {})
    for lang_code, audio_url in payload.items():
        if lang_code == "fr" or lang_code not in SUPPORTED_LANGUAGES:
            continue  # le français n'a pas besoin d'enregistrement
        # Valeur vide → suppression de l'enregistrement pour cette langue
        if not audio_url:
            cleaned.pop(lang_code, None)
            continue
        audio = str(audio_url).strip()
        if not audio.startswith(("https://", "/audio/")):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="L'enregistrement doit être une URL https:// ou un chemin /audio/…",
            )
        cleaned[lang_code] = {"audio_url": audio}

    question.translations = cleaned
    db.add(AuditLog(actor_id=current_user.id, action="question.audio_updated",
                    entity="question", entity_id=question.id,
                    details={"languages": list(cleaned.keys())}))
    db.commit()
    db.refresh(question)
    return question

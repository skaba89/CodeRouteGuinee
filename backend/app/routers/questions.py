from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.media_policy import validate_media_url
from app.models_audit import AuditLog
from app.models_question import Question
from app.models_user import User
from app.schemas import QuestionCreate, QuestionMediaUpdate, QuestionRejectionRequest, QuestionOfficialImportRequest, QuestionOfficialImportResult, QuestionRead

router = APIRouter(prefix="/questions", tags=["questions"])


def _validated_media_url(media_url: str, media_type: str | None) -> str:
    """Traduit la politique média centrale en erreur API 422 exploitable par l'UI."""
    try:
        return validate_media_url(media_url, media_type or "image")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_EXAM_MEDIA", "message": str(exc)},
        ) from exc


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
    data = payload.model_dump()
    if payload.media_url:
        media_type = payload.media_type or "image"
        data["media_type"] = media_type
        data["media_url"] = _validated_media_url(payload.media_url, media_type)
    question = Question(**data)
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
    validated_media: dict[tuple[str, str], tuple[str, str]] = {}

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
        if row.media_url:
            media_type = row.media_type or "image"
            validated_media[key] = (media_type, _validated_media_url(row.media_url, media_type))

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
        if key in validated_media:
            question.media_type, question.media_url = validated_media[key]
        else:
            question.media_type = None
            question.media_url = None
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
                "with_media": len(validated_media),
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
    """Associe un média sûr à une question sans modifier son contenu métier."""
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable")

    if payload.media_url is None:
        question.media_type = None
        question.media_url = None
        question.media_alt = None
    else:
        media_type = payload.media_type or "image"
        question.media_type = media_type
        question.media_url = _validated_media_url(payload.media_url, media_type)
        question.media_alt = (payload.media_alt or "").strip() or None

    db.add(AuditLog(
        actor_id=current_user.id,
        action="question.media_updated",
        entity="question",
        entity_id=question.id,
        details={
            "media_type": question.media_type,
            "has_media": question.media_url is not None,
            "media_host": urlsplit(question.media_url).hostname if question.media_url else None,
            "has_alt": bool(question.media_alt),
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
    """Génère la signature Cloudinary et la politique de validation pré-upload."""
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
    """Valide officiellement une question (super_admin uniquement — autorité DNTT)."""
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
    rows = db.execute(
        select(Question.validation_status, func.count())
        .group_by(Question.validation_status)
    ).all()
    by_status = {status_name: count for status_name, count in rows}
    total = sum(by_status.values())
    approved = by_status.get("approved", 0)
    from app.exam_engine import EXAM_QUESTIONS_TOTAL, CATEGORY_DISTRIBUTION

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


@router.get("/media-coverage",
            dependencies=[Depends(require_roles("admin", "super_admin"))])
def media_coverage(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """Mesure la couverture et la qualité minimale des médias de la banque active."""
    questions = list(db.scalars(select(Question).where(Question.is_active.is_(True))).all())
    total = len(questions)
    with_media = [q for q in questions if q.media_url]
    images = [q for q in with_media if q.media_type == "image"]
    videos = [q for q in with_media if q.media_type == "video"]
    missing_alt = [q for q in with_media if not (q.media_alt or "").strip()]
    insecure_urls = [q for q in with_media if not str(q.media_url).startswith("https://")]
    approved = [q for q in questions if q.validation_status == "approved"]
    approved_with_media = [q for q in approved if q.media_url]

    return {
        "questions_total": total,
        "with_media": len(with_media),
        "without_media": total - len(with_media),
        "coverage_percent": round(len(with_media) / total * 100, 1) if total else 0.0,
        "images": len(images),
        "videos": len(videos),
        "missing_alt": len(missing_alt),
        "insecure_legacy_urls": len(insecure_urls),
        "approved_questions": len(approved),
        "approved_with_media": len(approved_with_media),
        "approved_media_percent": round(len(approved_with_media) / len(approved) * 100, 1) if approved else 0.0,
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
            continue
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


@router.get("/audio-coverage",
            dependencies=[Depends(require_roles("admin", "super_admin"))])
def audio_coverage(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """Couverture des enregistrements audio par langue nationale."""
    LANGUAGE_NAMES = {
        "ff": "Pular", "man": "Malinké", "sus": "Soussou",
        "kss": "Kissi", "gkp": "Kpelle", "lom": "Toma",
    }

    questions = list(db.scalars(select(Question).where(Question.is_active.is_(True))).all())
    total = len(questions)

    languages = []
    for code, name in LANGUAGE_NAMES.items():
        recorded = sum(
            1 for q in questions
            if isinstance(q.translations, dict)
            and isinstance(q.translations.get(code), dict)
            and q.translations[code].get("audio_url")
        )
        languages.append({
            "code": code,
            "name": name,
            "recorded": recorded,
            "total": total,
            "percent": round(recorded / total * 100, 1) if total else 0.0,
        })

    return {
        "questions_total": total,
        "languages": languages,
        "note": "Les questions sans enregistrement utilisent la synthèse vocale "
                "(repli automatique). Le texte reste affiché en français.",
    }

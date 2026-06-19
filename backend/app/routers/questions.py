from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_question import Question
from app.models_user import User
from app.schemas import QuestionCreate, QuestionOfficialImportRequest, QuestionOfficialImportResult, QuestionRead

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=list[QuestionRead])
def list_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> list[Question]:
    return list(db.scalars(select(Question).where(Question.is_active.is_(True))).all())


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

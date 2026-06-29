"""
Endpoints e-learning — CodeRoute Guinée

Public (avec auth candidat) :
  GET /courses                       — liste des cours actifs
  GET /courses/{course_id}           — un cours + ses leçons
  GET /courses/{id}/lessons/{lid}    — une leçon
  POST /courses/{id}/lessons/{lid}/progress — enregistrer la progression

Admin :
  POST /admin/courses                — créer un cours
  PUT  /admin/courses/{id}           — modifier un cours
  DELETE /admin/courses/{id}         — supprimer
  POST /admin/courses/{id}/lessons   — ajouter une leçon
  PUT  /admin/courses/{id}/lessons/{lid}  — modifier une leçon
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models_elearning import Course, Lesson, LessonProgress
from app.models_user import User

# ── Routers ───────────────────────────────────────────────────────────────────
router_public = APIRouter(prefix="/courses", tags=["e-learning"])
router_admin  = APIRouter(prefix="/admin/courses", tags=["admin-elearning"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LessonRead(BaseModel):
    id: str
    title: str
    content: str
    order: int
    video_url: str | None = None
    video_duration_seconds: int | None = None
    duration_minutes: int
    slug: str | None = None

    model_config = {"from_attributes": True}


class CourseRead(BaseModel):
    id: str
    title: str
    description: str
    category: str
    order: int
    cover_url: str | None = None
    lesson_count: int = 0

    model_config = {"from_attributes": True}


class CourseDetailRead(CourseRead):
    lessons: list[LessonRead] = []


class CourseCreate(BaseModel):
    title: str
    description: str = ""
    category: str = "general"
    order: int = 0
    cover_url: str | None = None


class LessonCreate(BaseModel):
    title: str
    content: str = ""
    order: int = 0
    video_url: str | None = None
    video_duration_seconds: int | None = None
    duration_minutes: int = 5
    slug: str | None = None


class ProgressUpdate(BaseModel):
    progress_pct: int   # 0-100
    completed: bool = False


# ── Endpoints publics ─────────────────────────────────────────────────────────

@router_public.get("", response_model=list[CourseRead])
def list_courses(
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseRead]:
    """Liste tous les cours actifs, avec le nombre de leçons."""
    q = select(Course).where(Course.is_active.is_(True)).order_by(Course.order, Course.title)
    if category:
        q = q.where(Course.category == category)
    courses = db.scalars(q).all()
    return [
        CourseRead(
            id=c.id, title=c.title, description=c.description,
            category=c.category, order=c.order, cover_url=c.cover_url,
            lesson_count=len([ls for ls in c.lessons if ls.is_active]),
        )
        for c in courses
    ]


@router_public.get("/{course_id}", response_model=CourseDetailRead)
def get_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseDetailRead:
    """Un cours complet avec toutes ses leçons actives."""
    course = db.scalar(select(Course).where(Course.id == course_id, Course.is_active.is_(True)))
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable")

    active_lessons = [lesson for lesson in course.lessons if lesson.is_active]
    return CourseDetailRead(
        id=course.id, title=course.title, description=course.description,
        category=course.category, order=course.order, cover_url=course.cover_url,
        lesson_count=len(active_lessons),
        lessons=[LessonRead.model_validate(lsn) for lsn in active_lessons],
    )


@router_public.get("/{course_id}/lessons/{lesson_id}", response_model=LessonRead)
def get_lesson(
    course_id: str,
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LessonRead:
    """Une leçon individuelle."""
    lesson = db.scalar(
        select(Lesson).where(
            Lesson.id == lesson_id,
            Lesson.course_id == course_id,
            Lesson.is_active.is_(True),
        )
    )
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leçon introuvable")
    return LessonRead.model_validate(lesson)


@router_public.post("/{course_id}/lessons/{lesson_id}/progress")
def update_progress(
    course_id: str,
    lesson_id: str,
    payload: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "admin", "super_admin")),
) -> dict:
    """Enregistre ou met à jour la progression d'un candidat sur une leçon."""
    from app.models_candidate import Candidate

    lesson = db.scalar(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
    )
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leçon introuvable")

    # Récupérer le candidat lié à l'utilisateur
    candidate = db.scalar(select(Candidate).where(Candidate.email == current_user.email))
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun profil candidat associé à ce compte"
        )

    pct = max(0, min(100, payload.progress_pct))

    # Upsert progression
    prog = db.scalar(
        select(LessonProgress).where(
            LessonProgress.candidate_id == candidate.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    if prog:
        prog.progress_pct = max(prog.progress_pct, pct)
        prog.completed    = payload.completed or prog.completed
        prog.last_seen_at = now
        if payload.completed and not prog.completed_at:
            prog.completed_at = now
    else:
        prog = LessonProgress(
            candidate_id  = candidate.id,
            lesson_id     = lesson_id,
            progress_pct  = pct,
            completed     = payload.completed,
            last_seen_at  = now,
            completed_at  = now if payload.completed else None,
        )
        db.add(prog)

    db.commit()
    return {
        "lesson_id":    lesson_id,
        "progress_pct": prog.progress_pct,
        "completed":    prog.completed,
    }


# ── Endpoints admin ───────────────────────────────────────────────────────────

@router_admin.post("", status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CourseRead:
    """Créer un nouveau cours."""
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseRead(
        id=course.id, title=course.title, description=course.description,
        category=course.category, order=course.order, cover_url=course.cover_url,
        lesson_count=0,
    )


@router_admin.put("/{course_id}")
def update_course(
    course_id: str,
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CourseRead:
    """Modifier un cours existant."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    for k, v in payload.model_dump().items():
        setattr(course, k, v)
    db.commit()
    return CourseRead(
        id=course.id, title=course.title, description=course.description,
        category=course.category, order=course.order, cover_url=course.cover_url,
        lesson_count=len(course.lessons),
    )


@router_admin.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> None:
    """Supprimer un cours (super_admin uniquement)."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    db.delete(course)
    db.commit()


@router_admin.post("/{course_id}/lessons", status_code=status.HTTP_201_CREATED)
def create_lesson(
    course_id: str,
    payload: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> LessonRead:
    """Ajouter une leçon à un cours."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Cours introuvable")
    lesson = Lesson(course_id=course_id, **payload.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return LessonRead.model_validate(lesson)


@router_admin.put("/{course_id}/lessons/{lesson_id}")
def update_lesson(
    course_id: str,
    lesson_id: str,
    payload: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> LessonRead:
    """Modifier une leçon."""
    lesson = db.scalar(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.course_id == course_id)
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Leçon introuvable")
    for k, v in payload.model_dump().items():
        setattr(lesson, k, v)
    db.commit()
    return LessonRead.model_validate(lesson)

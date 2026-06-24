"""
Modèles E-learning — CodeRoute Guinée

Course : un module de cours (ex : "Signalisation verticale")
Lesson : une leçon dans un cours (texte + vidéo optionnelle)
LessonProgress : progression d'un candidat sur les leçons
"""
from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid4() -> str:
    return str(_uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Course(Base):
    __tablename__ = "courses"

    id:          Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4)
    title:       Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category:    Mapped[str] = mapped_column(String(80), default="general")
    # Ordre d'affichage
    order:       Mapped[int] = mapped_column(Integer, default=0)
    is_active:   Mapped[bool] = mapped_column(Boolean, default=True)
    # Miniature / illustration
    cover_url:   Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at:  Mapped[datetime] = mapped_column(default=_now)
    updated_at:  Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    lessons: Mapped[list[Lesson]] = relationship(
        "Lesson", back_populates="course",
        cascade="all, delete-orphan",
        order_by="Lesson.order"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id:          Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4)
    course_id:   Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), nullable=False)
    title:       Mapped[str] = mapped_column(String(200), nullable=False)
    content:     Mapped[str] = mapped_column(Text, default="")
    order:       Mapped[int] = mapped_column(Integer, default=0)
    # Vidéo
    video_url:   Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Durée de lecture estimée (minutes)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=5)
    is_active:   Mapped[bool] = mapped_column(Boolean, default=True)
    # Slug URL-friendly
    slug:        Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at:  Mapped[datetime] = mapped_column(default=_now)
    updated_at:  Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    course:   Mapped[Course] = relationship("Course", back_populates="lessons")
    progress: Mapped[list[LessonProgress]] = relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("candidate_id", "lesson_id", name="uq_lesson_progress"),
    )

    id:           Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False)
    lesson_id:    Mapped[str] = mapped_column(String(36), ForeignKey("lessons.id"), nullable=False)
    completed:    Mapped[bool] = mapped_column(Boolean, default=False)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)   # 0-100
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    lesson: Mapped[Lesson] = relationship("Lesson", back_populates="progress")

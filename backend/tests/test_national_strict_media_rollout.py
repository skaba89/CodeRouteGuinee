from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.exam_engine import CATEGORY_DISTRIBUTION, EXAM_QUESTIONS_TOTAL
from app.models_question import Question
from app.national_governance import build_readiness, technical_contract
from app.routers import national_readiness as national_readiness_router
import app.national_governance as national_governance


def _seed_isolated_official_bank(db) -> None:
    for question in db.scalars(select(Question)).all():
        question.is_active = False

    questions: list[Question] = []
    sequence = 0
    for category, required in CATEGORY_DISTRIBUTION.items():
        for index in range(required):
            sequence += 1
            questions.append(
                Question(
                    category=category,
                    text=f"Question nationale média stricte {category} {index + 1} #{sequence}",
                    options=["A", "B", "C"],
                    correct_answer="A",
                    explanation="Recette du gate média national.",
                    is_active=True,
                    validation_status="approved",
                )
            )
    db.add_all(questions)
    db.flush()
    assert len(questions) == EXAM_QUESTIONS_TOTAL


def _legacy_media_summary() -> dict:
    return {
        "approved_questions": EXAM_QUESTIONS_TOTAL,
        "runtime_ready_questions": EXAM_QUESTIONS_TOTAL,
        "strict_ready_questions": 0,
        "runtime_exam_constructible": True,
        "strict_exam_constructible": False,
        "legacy_migration_required": True,
        "legacy_remaining": EXAM_QUESTIONS_TOTAL,
        "counts_by_mode": {"legacy_compatibility": EXAM_QUESTIONS_TOTAL},
        "blocked_questions_total": 0,
        "institutional_validation_inferred": False,
    }


def _strict_media_summary() -> dict:
    return {
        "approved_questions": EXAM_QUESTIONS_TOTAL,
        "runtime_ready_questions": EXAM_QUESTIONS_TOTAL,
        "strict_ready_questions": EXAM_QUESTIONS_TOTAL,
        "runtime_exam_constructible": True,
        "strict_exam_constructible": True,
        "legacy_migration_required": False,
        "legacy_remaining": 0,
        "counts_by_mode": {"normalized": EXAM_QUESTIONS_TOTAL},
        "blocked_questions_total": 0,
        "institutional_validation_inferred": False,
    }


def _active_policy() -> dict:
    return {
        "reference": "DNTT-POLICY-MEDIA-2099.1",
        "document": {"parameters": technical_contract()},
    }


def test_governance_readiness_blocks_national_go_live_for_legacy_media(monkeypatch) -> None:
    init_db()
    with SessionLocal() as db:
        _seed_isolated_official_bank(db)
        monkeypatch.setattr(national_governance, "active_policy", lambda _db: _active_policy())
        monkeypatch.setattr(
            national_governance,
            "build_national_media_readiness",
            lambda _db, _questions: _legacy_media_summary(),
        )

        readiness = build_readiness(db)
        question_bank = next(item for item in readiness["checks"] if item["code"] == "official_question_bank")
        media_bank = next(item for item in readiness["checks"] if item["code"] == "official_media_bank")

        assert question_bank["status"] == "pass"
        assert media_bank["status"] == "fail"
        assert media_bank["evidence"]["runtime_exam_constructible"] is True
        assert media_bank["evidence"]["strict_exam_constructible"] is False
        assert media_bank["evidence"]["legacy_remaining"] == EXAM_QUESTIONS_TOTAL
        assert media_bank["evidence"]["institutional_validation_inferred"] is False
        assert "official_media_bank_not_strict_ready" in readiness["blockers"]
        assert readiness["go_live_allowed"] is False
        db.rollback()


def test_governance_readiness_lifts_only_the_media_blocker_when_strict_bank_is_ready(monkeypatch) -> None:
    init_db()
    with SessionLocal() as db:
        _seed_isolated_official_bank(db)
        monkeypatch.setattr(national_governance, "active_policy", lambda _db: _active_policy())
        monkeypatch.setattr(
            national_governance,
            "build_national_media_readiness",
            lambda _db, _questions: _strict_media_summary(),
        )

        readiness = build_readiness(db)
        media_bank = next(item for item in readiness["checks"] if item["code"] == "official_media_bank")

        assert media_bank["status"] == "pass"
        assert media_bank["evidence"]["strict_ready_questions"] == EXAM_QUESTIONS_TOTAL
        assert media_bank["evidence"]["legacy_remaining"] == 0
        assert "official_media_bank_not_strict_ready" not in readiness["blockers"]
        db.rollback()


def test_national_dashboard_keeps_legacy_bank_pilot_compatible_but_blocks_rollout(monkeypatch) -> None:
    init_db()
    with SessionLocal() as db:
        _seed_isolated_official_bank(db)
        monkeypatch.setattr(
            national_readiness_router,
            "build_national_media_readiness",
            lambda _db, _questions: _legacy_media_summary(),
        )

        readiness = national_readiness_router.get_national_readiness(db=db, current_user=None)
        official = readiness["official_bank"]

        assert official["pedagogical_ready"] is True
        assert official["pilot_compatible"] is True
        assert official["national_strict_ready"] is False
        assert official["media"]["runtime_ready_questions"] == EXAM_QUESTIONS_TOTAL
        assert official["media"]["strict_ready_questions"] == 0
        assert official["media"]["legacy_remaining"] == EXAM_QUESTIONS_TOTAL
        assert official["media"]["institutional_validation_inferred"] is False
        assert readiness["pillars"]["official_question_bank"]["pilot_compatible"] is True
        assert readiness["pillars"]["official_question_bank"]["ready"] is False
        assert "official_media_bank_not_strict_ready" in readiness["blockers"]
        assert readiness["national_rollout_allowed"] is False
        db.rollback()


def test_national_dashboard_lifts_media_blocker_for_strict_bank(monkeypatch) -> None:
    init_db()
    with SessionLocal() as db:
        _seed_isolated_official_bank(db)
        monkeypatch.setattr(
            national_readiness_router,
            "build_national_media_readiness",
            lambda _db, _questions: _strict_media_summary(),
        )

        readiness = national_readiness_router.get_national_readiness(db=db, current_user=None)
        official = readiness["official_bank"]

        assert official["pedagogical_ready"] is True
        assert official["pilot_compatible"] is True
        assert official["national_strict_ready"] is True
        assert official["media"]["strict_ready_questions"] == EXAM_QUESTIONS_TOTAL
        assert official["media"]["legacy_remaining"] == 0
        assert readiness["pillars"]["official_question_bank"]["ready"] is True
        assert "official_media_bank_not_strict_ready" not in readiness["blockers"]
        db.rollback()

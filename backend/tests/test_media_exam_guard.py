from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.media_runtime_resolver import ResolvedExamMedia
from app.routers import exam_media_guard, exams


def test_exam_question_guard_replaces_exactly_one_legacy_route():
    matches = [
        route
        for route in exams.router.routes
        if getattr(route, "path", None) == "/exams/{attempt_id}/questions"
        and "GET" in (getattr(route, "methods", set()) or set())
    ]
    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "app.routers.exam_media_guard"


def test_guard_serializes_resolved_media_without_answer_or_governance_leak(monkeypatch):
    attempt = SimpleNamespace(id="attempt-1", status="started")
    trace = SimpleNamespace(question_ids=["q-video", "q-image"], question_count=2)
    q_image = SimpleNamespace(
        id="q-image",
        category="signalisation",
        text="Question image",
        options=["A", "B"],
    )
    q_video = SimpleNamespace(
        id="q-video",
        category="priorites",
        text="Question vidéo",
        options=["A", "B", "C"],
    )

    db = MagicMock()
    db.scalar.side_effect = [attempt, trace]
    db.scalars.return_value.all.return_value = [q_image, q_video]

    monkeypatch.setattr(exam_media_guard, "_assert_attempt_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(exam_media_guard, "_require_official_trace", lambda value: value)
    monkeypatch.setattr(
        exam_media_guard,
        "resolve_question_content",
        lambda question, _lang: {
            "text": question.text,
            "options": question.options,
            "audio_url": None,
        },
    )
    monkeypatch.setattr(
        exam_media_guard,
        "resolve_exam_media_batch",
        lambda _db, question_ids: [
            ResolvedExamMedia(
                question_id="q-video",
                source="normalized",
                media_type="video",
                media_url="https://media.example/video.mp4",
                media_alt="Situation de conduite — thème PRIORITES",
                poster_url="https://media.example/poster.webp",
                fallback_url="https://media.example/fallback.webp",
                fallback_media_type="image",
                degraded=False,
            ),
            ResolvedExamMedia(
                question_id="q-image",
                source="legacy",
                media_type="image",
                media_url="https://media.example/image.webp",
                media_alt="Situation de conduite",
                degraded=True,
                fallback_reason="normalized_primary_not_publishable",
            ),
        ],
    )

    response = exam_media_guard.get_exam_questions_with_resolved_media(
        "attempt-1",
        lang="fr",
        db=db,
        current_user=SimpleNamespace(role="admin", id="admin-1"),
    )

    assert [item.id for item in response.questions] == ["q-video", "q-image"]
    video = response.questions[0]
    assert video.media_type == "video"
    assert video.media_url == "https://media.example/video.mp4"
    assert video.media_poster_url == "https://media.example/poster.webp"
    assert video.media_fallback_url == "https://media.example/fallback.webp"
    assert video.media_source == "normalized"
    assert video.media_degraded is False

    image = response.questions[1]
    assert image.media_source == "legacy"
    assert image.media_degraded is True

    serialized = response.model_dump()
    serialized_text = repr(serialized)
    assert "correct_answer" not in serialized_text
    assert "explanation" not in serialized_text
    assert "license_reference" not in serialized_text
    assert "regulatory_authority_reference" not in serialized_text
    assert "source_reference" not in serialized_text

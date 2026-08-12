from datetime import UTC, datetime
from uuid import uuid4

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_media import MediaAsset, QuestionMedia
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.routers.exam_media_questions import get_exam_questions_with_runtime_media


def _image(url: str, theme: str) -> MediaAsset:
    return MediaAsset(
        media_type="image", usage_type="exam", secure_url=url,
        mime_type="image/webp", width=1920, height=1080,
        file_size_bytes=700_000, checksum_sha256=uuid4().hex + uuid4().hex,
        theme=theme, country_code="GN", source_type="original",
        source_reference=f"TEST-{theme}", copyright_owner="CodeRoute Guinée",
        quality_status="validated", regulatory_status="validated",
        regulatory_authority_reference=f"DNTT-{theme}",
    )


def test_app_installs_media_aware_exam_questions_handler() -> None:
    matching = [
        route for route in app.routes
        if getattr(route, "path", None) == "/api/v1/exams/{attempt_id}/questions"
        and "GET" in (getattr(route, "methods", None) or set())
    ]
    assert len(matching) == 1
    assert matching[0].endpoint.__name__ == "get_exam_questions_with_runtime_media"


def test_media_aware_handler_serves_normalized_image_and_video() -> None:
    init_db()
    suffix = uuid4().hex[:10]
    image_url = f"https://media.example/{suffix}-image.webp"
    video_url = f"https://media.example/{suffix}-video.mp4"
    poster_url = f"https://media.example/{suffix}-poster.webp"
    fallback_url = f"https://media.example/{suffix}-fallback.webp"

    with SessionLocal() as db:
        center = Center(code=f"M-{suffix}", name="Centre Media", city="Conakry", address="Test", status="accredited")
        candidate = Candidate(
            reference=f"GN-M-{suffix}", first_name="Mamadou", last_name="Camara",
            identity_number=f"ID-{suffix}", phone="+224620000001", permit_category="B", status="verified",
        )
        db.add_all([center, candidate]); db.flush()
        session = ExamSession(
            reference=f"S-M-{suffix}", center_id=center.id,
            starts_at=datetime.now(UTC).replace(tzinfo=None), capacity=35,
        )
        q_image = Question(
            category="signalisation", text=f"Image {suffix}", options=["A", "B"], correct_answer="A",
            validation_status="approved", is_active=True,
        )
        q_video = Question(
            category="priorites", text=f"Video {suffix}", options=["A", "B"], correct_answer="A",
            validation_status="approved", is_active=True,
        )
        image = _image(image_url, "SIGNALISATION")
        poster = _image(poster_url, "POSTER")
        fallback = _image(fallback_url, "FALLBACK")
        db.add_all([session, q_image, q_video, image, poster, fallback]); db.flush()
        video = MediaAsset(
            media_type="video", usage_type="exam", secure_url=video_url,
            mime_type="video/mp4", width=1920, height=1080, duration_seconds=12,
            file_size_bytes=6_000_000, checksum_sha256=uuid4().hex + uuid4().hex,
            poster_media_id=poster.id, fallback_media_id=fallback.id, theme="PRIORITES",
            country_code="GN", source_type="original", source_reference="TEST-VIDEO",
            copyright_owner="CodeRoute Guinée", quality_status="validated", regulatory_status="validated",
            regulatory_authority_reference="DNTT-VIDEO",
        )
        db.add(video); db.flush()
        db.add_all([
            QuestionMedia(question_id=q_image.id, media_id=image.id, role="primary"),
            QuestionMedia(question_id=q_video.id, media_id=video.id, role="primary"),
        ])
        attempt = ExamAttempt(candidate_id=candidate.id, session_id=session.id)
        db.add(attempt); db.flush()
        db.add(ExamQuestionTrace(
            attempt_id=attempt.id, question_ids=[q_image.id, q_video.id], question_count=2,
            bank_hash=f"bank-{suffix}", version_label=f"media-{suffix}", selection_mode="test",
        ))
        db.commit()

        result = get_exam_questions_with_runtime_media(
            attempt_id=attempt.id,
            db=db,
            current_user=User(role="admin", email="admin@example.test", full_name="Admin", password_hash="unused"),
        )

        by_id = {item.id: item for item in result.questions}
        assert by_id[q_image.id].media_url == image_url
        assert by_id[q_image.id].media_type == "image"
        assert by_id[q_video.id].media_url == video_url
        assert by_id[q_video.id].media_type == "video"
        assert by_id[q_video.id].poster_url == poster_url
        assert by_id[q_video.id].fallback_url == fallback_url

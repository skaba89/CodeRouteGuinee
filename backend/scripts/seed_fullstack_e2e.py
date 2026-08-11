"""Seed minimal et idempotent pour le vrai E2E PostgreSQL + navigateur."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User
from app.security import get_password_hash

EMAIL = "e2e.candidate@coderoute.test"
PASSWORD = "FullstackTest123!"
CENTER_CODE = "E2E-KALOUM-001"
CENTER_NAME = "E2E Centre Kaloum"
SESSION_REFERENCE = "GN-SESSION-E2E-FULLSTACK"
CANDIDATE_REFERENCE = "GN-CODE-E2E-FULLSTACK"


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        center = db.scalar(select(Center).where(Center.code == CENTER_CODE))
        if center is None:
            center = Center(
                code=CENTER_CODE,
                name=CENTER_NAME,
                city="Conakry",
                commune="Kaloum",
                prefecture="Conakry",
                address="E2E Avenue de la République",
                capacity=35,
                max_sessions_per_week=3,
                status="accredited",
            )
            db.add(center)
            db.flush()

        user = db.scalar(select(User).where(User.email == EMAIL))
        if user is None:
            user = User(
                email=EMAIL,
                full_name="Candidat E2E",
                password_hash=get_password_hash(PASSWORD),
                role="candidate",
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.password_hash = get_password_hash(PASSWORD)
            user.role = "candidate"
            user.is_active = True
            db.add(user)

        candidate = db.scalar(select(Candidate).where(Candidate.reference == CANDIDATE_REFERENCE))
        if candidate is None:
            candidate = Candidate(
                reference=CANDIDATE_REFERENCE,
                first_name="Candidat",
                last_name="E2E",
                identity_number="E2E-ID-000001",
                phone="+224622000099",
                email=EMAIL,
                permit_category="B",
                city="Conakry",
                user_id=user.id,
                status="registered",
                attempt_count=0,
            )
            db.add(candidate)
        else:
            candidate.user_id = user.id
            candidate.email = EMAIL
            candidate.attempt_count = 0
            db.add(candidate)

        session = db.scalar(select(ExamSession).where(ExamSession.reference == SESSION_REFERENCE))
        target_start = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3)
        target_start = target_start.replace(hour=10, minute=0, second=0, microsecond=0)
        if session is None:
            session = ExamSession(
                reference=SESSION_REFERENCE,
                center_id=center.id,
                starts_at=target_start,
                capacity=35,
                status="planned",
            )
            db.add(session)
        else:
            session.center_id = center.id
            session.starts_at = target_start
            session.capacity = 35
            session.status = "planned"
            db.add(session)

        db.commit()
        print(f"FULLSTACK_E2E_EMAIL={EMAIL}")
        print(f"FULLSTACK_E2E_PASSWORD={PASSWORD}")
        print(f"FULLSTACK_E2E_CENTER={CENTER_NAME}")
        print(f"FULLSTACK_E2E_EXPECTED_QUOTE_GNF=150000")
    finally:
        db.close()


if __name__ == "__main__":
    main()

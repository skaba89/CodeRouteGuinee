from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_payment import Payment
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.security import get_password_hash

DEMO_ADMIN_EMAIL = "admin@coderoute.gov.gn"
DEMO_ADMIN_PASSWORD = "password123"
DEMO_CENTER_CODE = "CRG-CONAKRY-001"
DEMO_CANDIDATE_REFERENCE = "CRG-CAND-DEMO-001"
DEMO_SESSION_REFERENCE = "CRG-SESSION-DEMO-001"
DEMO_BOOKING_REFERENCE = "CRG-BOOK-DEMO-001"
DEMO_VERIFICATION_CODE = "CRG-VERIFY-DEMO-001"
DEMO_PAYMENT_REFERENCE = "CRG-PAY-DEMO-001"


def get_or_create_admin(db) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_ADMIN_EMAIL))
    if user:
        return user
    user = User(
        email=DEMO_ADMIN_EMAIL,
        full_name="Administrateur National CodeRoute",
        password_hash=get_password_hash(DEMO_ADMIN_PASSWORD),
        role="super_admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_center(db) -> Center:
    center = db.scalar(select(Center).where(Center.code == DEMO_CENTER_CODE))
    if center:
        return center
    center = Center(
        code=DEMO_CENTER_CODE,
        name="Centre agree Conakry Kaloum",
        city="Conakry",
        address="Kaloum, Boulevard de la Republique",
        capacity=30,
        status="active",
    )
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


def get_or_create_candidate(db) -> Candidate:
    candidate = db.scalar(select(Candidate).where(Candidate.reference == DEMO_CANDIDATE_REFERENCE))
    if candidate:
        return candidate
    candidate = Candidate(
        reference=DEMO_CANDIDATE_REFERENCE,
        first_name="Mamadou",
        last_name="Diallo",
        identity_number="GN-CNI-DEMO-001",
        phone="+224620000001",
        permit_category="B",
        status="registered",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_or_create_questions(db) -> list[Question]:
    existing = db.scalars(select(Question).where(Question.category == "demo")).all()
    if len(existing) >= 5:
        return existing
    questions = [
        Question(
            category="demo",
            text="Que signifie un feu rouge fixe ?",
            options=["S'arreter", "Accelerer", "Klaxonner", "Changer de voie"],
            correct_answer="S'arreter",
            explanation="Le feu rouge impose l'arret complet du vehicule.",
        ),
        Question(
            category="demo",
            text="Quelle distance de securite faut-il garder en circulation normale ?",
            options=["Une distance suffisante", "Aucune", "10 cm", "Toujours 1 metre"],
            correct_answer="Une distance suffisante",
            explanation="La distance doit permettre de reagir en cas de freinage.",
        ),
        Question(
            category="demo",
            text="Que faut-il faire avant de depasser ?",
            options=["Verifier, signaler, depasser", "Depasser sans regarder", "Freiner brusquement", "Fermer les yeux"],
            correct_answer="Verifier, signaler, depasser",
            explanation="Le depassement exige controle, signalisation et prudence.",
        ),
        Question(
            category="demo",
            text="Le port de la ceinture est-il obligatoire ?",
            options=["Oui", "Non", "Seulement la nuit", "Seulement en ville"],
            correct_answer="Oui",
            explanation="La ceinture protege le conducteur et les passagers.",
        ),
        Question(
            category="demo",
            text="Que faire en cas de panne sur la route ?",
            options=["Se signaler et securiser", "Rester au milieu", "Eteindre les feux", "Bloquer la voie"],
            correct_answer="Se signaler et securiser",
            explanation="Il faut proteger les autres usagers et prevenir le danger.",
        ),
    ]
    db.add_all(questions)
    db.commit()
    return db.scalars(select(Question).where(Question.category == "demo")).all()


def get_or_create_session(db, center: Center) -> ExamSession:
    session = db.scalar(select(ExamSession).where(ExamSession.reference == DEMO_SESSION_REFERENCE))
    if session:
        return session
    session = ExamSession(
        reference=DEMO_SESSION_REFERENCE,
        center_id=center.id,
        starts_at=datetime.utcnow() + timedelta(days=1),
        capacity=30,
        status="planned",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_or_create_booking(db, candidate: Candidate, session: ExamSession) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.reference == DEMO_BOOKING_REFERENCE))
    if booking:
        return booking
    booking = Booking(
        reference=DEMO_BOOKING_REFERENCE,
        candidate_id=candidate.id,
        session_id=session.id,
        status="confirmed",
        verification_code=DEMO_VERIFICATION_CODE,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_or_create_payment(db, booking: Booking) -> Payment:
    payment = db.scalar(select(Payment).where(Payment.reference == DEMO_PAYMENT_REFERENCE))
    if payment:
        return payment
    payment = Payment(
        reference=DEMO_PAYMENT_REFERENCE,
        booking_reference=booking.reference,
        amount_gnf=250000,
        provider="orange_money",
        phone="+224620000001",
        status="paid",
        receipt_number="CRG-RECEIPT-DEMO-001",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_or_create_attempt(db, candidate: Candidate, session: ExamSession, questions: list[Question]) -> ExamAttempt:
    attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.candidate_id == candidate.id, ExamAttempt.session_id == session.id))
    if attempt:
        return attempt
    answers = {question.id: question.correct_answer for question in questions[:5]}
    attempt = ExamAttempt(
        candidate_id=candidate.id,
        session_id=session.id,
        status="submitted",
        answers=answers,
        score=len(answers),
        passed=True,
        submitted_at=datetime.utcnow(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def seed_demo() -> None:
    init_db()
    db = SessionLocal()
    try:
        admin = get_or_create_admin(db)
        center = get_or_create_center(db)
        candidate = get_or_create_candidate(db)
        questions = get_or_create_questions(db)
        session = get_or_create_session(db, center)
        booking = get_or_create_booking(db, candidate, session)
        payment = get_or_create_payment(db, booking)
        attempt = get_or_create_attempt(db, candidate, session, questions)
        print("CodeRoute Guinee demo data ready")
        print(f"Admin: {admin.email} / {DEMO_ADMIN_PASSWORD}")
        print(f"Center: {center.code} - {center.name}")
        print(f"Candidate: {candidate.reference} - {candidate.first_name} {candidate.last_name}")
        print(f"Booking: {booking.reference} / verification: {booking.verification_code}")
        print(f"Payment: {payment.reference} / receipt: {payment.receipt_number}")
        print(f"Exam attempt: {attempt.id} / score: {attempt.score}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()

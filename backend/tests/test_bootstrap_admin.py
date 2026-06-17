from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.bootstrap_admin import bootstrap_admin
from app.db.base import Base
from app.models_user import User
from app.security import verify_password


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def test_bootstrap_admin_creates_super_admin() -> None:
    db = make_db()
    try:
        user, created = bootstrap_admin(
            db,
            email="Admin@CodeRoute.gov.gn",
            password="StrongBootstrap123",
            full_name="Administrateur Institutionnel",
        )

        assert created is True
        assert user.email == "admin@coderoute.gov.gn"
        assert user.role == "super_admin"
        assert user.is_active is True
        assert verify_password("StrongBootstrap123", user.password_hash)
    finally:
        db.close()


def test_bootstrap_admin_reactivates_existing_user_without_resetting_password() -> None:
    db = make_db()
    try:
        user = User(
            email="admin@coderoute.gov.gn",
            full_name="Admin",
            password_hash="existing-hash",
            role="candidate",
            is_active=False,
        )
        db.add(user)
        db.commit()

        bootstrapped_user, created = bootstrap_admin(
            db,
            email="admin@coderoute.gov.gn",
            password="StrongBootstrap123",
            full_name="Administrateur Institutionnel",
        )

        assert created is False
        assert bootstrapped_user.role == "super_admin"
        assert bootstrapped_user.is_active is True
        assert bootstrapped_user.password_hash == "existing-hash"
    finally:
        db.close()

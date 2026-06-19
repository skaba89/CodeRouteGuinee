from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal, init_db
from app.models_user import User
from app.security import get_password_hash

MIN_BOOTSTRAP_PASSWORD_LENGTH = 12


def bootstrap_admin(
    db: Session,
    email: str,
    password: str,
    full_name: str,
) -> tuple[User, bool]:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user:
        if user.role != "super_admin" or not user.is_active:
            user.role = "super_admin"
            user.is_active = True
            db.commit()
            db.refresh(user)
        return user, False

    user = User(
        email=normalized_email,
        full_name=full_name.strip(),
        password_hash=get_password_hash(password),
        role="super_admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def bootstrap_admin_from_settings() -> None:
    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        raise RuntimeError("BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD are required")
    if len(settings.bootstrap_admin_password) < MIN_BOOTSTRAP_PASSWORD_LENGTH:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters")

    init_db()
    db = SessionLocal()
    try:
        user, created = bootstrap_admin(
            db=db,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
            full_name=settings.bootstrap_admin_full_name,
        )
        action = "created" if created else "verified"
        print(f"Super admin {action}: {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_admin_from_settings()

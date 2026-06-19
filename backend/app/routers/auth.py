from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_guard import LoginRateLimiter
from app.db.session import get_db
from app.core.config import get_settings
from app.deps import get_current_user
from app.models_audit import AuditLog
from app.models_user import User
from app.schemas import PasswordChangeRequest, Token, UserCreate, UserRead
from app.security import create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
PRIVILEGED_ROLES = {"admin", "super_admin"}
login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.login_rate_limit_attempts,
    window_seconds=settings.login_rate_limit_window_seconds,
)


def login_rate_limit_key(request: Request, email: str) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{client_ip}:{email.strip().lower()}"


def audit_auth_event(db: Session, action: str, email: str, request: Request, user: User | None = None) -> None:
    db.add(
        AuditLog(
            actor_id=user.id if user else None,
            action=action,
            entity="auth",
            entity_id=user.id if user else None,
            details={
                "email": email.strip().lower(),
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")[:255],
            },
        )
    )
    db.commit()


def requires_privileged_registration_token(role: str) -> bool:
    return role in PRIVILEGED_ROLES and (
        settings.environment == "production" or bool(settings.admin_registration_token)
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    x_admin_registration_token: str | None = Header(default=None),
) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if requires_privileged_registration_token(payload.role) and (
        not settings.admin_registration_token
        or x_admin_registration_token != settings.admin_registration_token
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Privileged role registration requires bootstrap authorization")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    key = login_rate_limit_key(request, form.username)
    if login_rate_limiter.is_blocked(key):
        audit_auth_event(db, "auth.login_blocked", form.username, request)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.password_hash):
        login_rate_limiter.register_failure(key)
        audit_auth_event(db, "auth.login_failed", form.username, request, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    login_rate_limiter.reset(key)
    audit_auth_event(db, "auth.login_success", form.username, request, user)
    return Token(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="auth.password_change_failed",
                entity="user",
                entity_id=current_user.id,
                details={"email": current_user.email},
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is invalid")

    current_user.password_hash = get_password_hash(payload.new_password)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="auth.password_changed",
            entity="user",
            entity_id=current_user.id,
            details={"email": current_user.email},
        )
    )
    db.commit()

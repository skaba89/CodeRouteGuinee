from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_guard import LoginRateLimiter
from app.core.config import get_settings
from app.csrf import generate_csrf_token, set_csrf_cookie
from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models_audit import AuditLog
from app.models_user import User
from app.schemas import PasswordChangeRequest, Token, UserCreate, UserRead
from app.security import create_access_token, create_refresh_token, decode_refresh_token, get_password_hash, verify_password
from app.two_factor import activate_2fa, check_2fa, disable_2fa, is_2fa_enabled, setup_2fa

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


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    x_admin_registration_token: str | None = Header(default=None),
) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if (
        payload.role in PRIVILEGED_ROLES
        and settings.admin_registration_token
        and x_admin_registration_token != settings.admin_registration_token
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
    if login_rate_limiter.is_blocked(key, db):
        audit_auth_event(db, "auth.login_blocked", form.username, request)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.password_hash):
        login_rate_limiter.register_failure(key, db)
        audit_auth_event(db, "auth.login_failed", form.username, request, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    login_rate_limiter.reset(key, db)
    audit_auth_event(db, "auth.login_success", form.username, request, user)
    return Token(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


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


class RefreshRequest(BaseModel):
    refresh_token: str





@router.get("/csrf-token", tags=["auth"])
def get_csrf_token(response: Response) -> dict:
    """
    Génère et retourne un token CSRF.
    Le token est aussi posé en cookie (X-CSRF-Token).
    Le frontend doit appeler cet endpoint au démarrage et inclure
    le token dans le header X-CSRF-Token de toutes les requêtes mutatives.
    """
    token = generate_csrf_token()
    set_csrf_cookie(response, token)
    return {"csrf_token": token, "header_name": "X-CSRF-Token"}


@router.post("/refresh", response_model=Token)
def refresh_token(
    payload_in: RefreshRequest,
    db: Session = Depends(get_db),
) -> Token:
    payload = decode_refresh_token(payload_in.refresh_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or unknown user")
    return Token(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
    )


# ── 2FA TOTP Endpoints ──────────────────────────────────────────────────────

@router.post("/2fa/setup", tags=["auth"])
def setup_two_factor(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center", "candidate")),
) -> dict:
    """
    Initialise la configuration 2FA pour l'utilisateur connecté.
    Retourne un QR code URI à scanner dans Google Authenticator.
    Le 2FA n'est PAS encore activé — il faut appeler /2fa/verify avec le premier code.
    """
    return setup_2fa(str(current_user.id), current_user.email, db)


@router.post("/2fa/verify", tags=["auth"])
def verify_and_activate_2fa(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center", "candidate")),
) -> dict:
    """
    Vérifie le code TOTP et active le 2FA si correct.
    Payload : {"code": "123456"}
    """
    code = payload.get("code", "")
    if not code:
        raise HTTPException(status_code=400, detail="Code TOTP requis")

    ok = activate_2fa(str(current_user.id), code, db)
    if not ok:
        raise HTTPException(status_code=400, detail="Code TOTP invalide ou 2FA déjà activé")

    return {"activated": True, "message": "2FA activé avec succès"}


@router.post("/2fa/check", tags=["auth"])
def check_two_factor(
    payload: dict,
    user_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Vérifie le code 2FA lors du login (appelé après la validation du mot de passe).
    Payload : {"code": "123456"}
    """
    code = payload.get("code", "")
    if not code:
        raise HTTPException(status_code=400, detail="Code 2FA requis")

    ok = check_2fa(user_id, code, db)
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Code 2FA invalide"
        )
    return {"valid": True}


@router.post("/2fa/disable", tags=["auth"])
def disable_two_factor(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center", "candidate")),
) -> dict:
    """Désactive le 2FA pour l'utilisateur connecté."""
    disable_2fa(str(current_user.id), db)
    return {"disabled": True}


@router.get("/2fa/status", tags=["auth"])
def get_2fa_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center", "candidate")),
) -> dict:
    """Retourne si le 2FA est activé pour l'utilisateur connecté."""
    enabled = is_2fa_enabled(str(current_user.id), db)
    return {"enabled": enabled, "user_id": str(current_user.id)}


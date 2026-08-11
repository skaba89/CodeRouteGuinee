from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_user import User
from app.routers import auth as auth_router
from app.security import (
    create_2fa_challenge_token,
    decode_2fa_challenge_token,
    decode_access_token,
    get_password_hash,
)


def _user(role: str = "center") -> User:
    init_db()
    db = SessionLocal()
    user = User(
        email=f"security-{role}-{uuid4().hex}@coderoute.test",
        full_name="Security invariant",
        password_hash=get_password_hash("TestPass123!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.expunge(user)
    db.close()
    return user


def test_2fa_challenge_is_not_an_access_token() -> None:
    user = _user("center")
    challenge = create_2fa_challenge_token(user.id, user.role)

    assert decode_2fa_challenge_token(challenge)["sub"] == user.id
    assert decode_access_token(challenge) is None

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {challenge}"},
        )
    assert response.status_code == 401


def test_2fa_check_requires_challenge_for_same_user() -> None:
    user = _user("center")
    other = _user("center")
    challenge = create_2fa_challenge_token(user.id, user.role)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/auth/2fa/check?user_id={other.id}",
            headers={"Authorization": f"Bearer {challenge}"},
            json={"code": "000000"},
        )
    assert response.status_code == 401
    assert "Challenge 2FA" in response.json()["detail"]


def test_center_registration_requires_bootstrap_authorization_when_configured(monkeypatch) -> None:
    token = "institutional-bootstrap-token-at-least-32-characters"
    monkeypatch.setattr(auth_router.settings, "admin_registration_token", token)
    email = f"public-center-{uuid4().hex}@coderoute.test"

    with TestClient(app) as client:
        denied = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "full_name": "Unauthorized center",
                "password": "TestPass123!",
                "role": "center",
            },
        )
        allowed = client.post(
            "/api/v1/auth/register",
            headers={"X-Admin-Registration-Token": token},
            json={
                "email": email,
                "full_name": "Authorized center",
                "password": "TestPass123!",
                "role": "center",
            },
        )

    assert denied.status_code == 403
    assert allowed.status_code == 201
    assert allowed.json()["role"] == "center"

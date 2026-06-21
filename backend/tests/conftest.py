"""
Fixtures partagées pour les tests E2E.
Fournit des helpers d'authentification pour les rôles super_admin, admin, center, candidate.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.models_user import User
from app.security import get_password_hash


def _create_test_user(role: str) -> tuple[str, str]:
    """Crée un utilisateur de test en base et retourne (email, password)."""
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    email = f"test-{role}-{suffix}@coderoute.test"
    password = "TestPass123!"
    try:
        user = User(
            email=email,
            full_name=f"Test {role.title()} {suffix}",
            password_hash=get_password_hash(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()
    return email, password


def get_auth_headers(client: TestClient, role: str = "super_admin") -> dict[str, str]:
    """Retourne les headers Authorization pour un rôle donné."""
    email, password = _create_test_user(role)
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for role {role}: {resp.json()}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_admin_headers(client: TestClient) -> dict[str, str]:
    return get_auth_headers(client, "super_admin")


def get_center_headers(client: TestClient) -> dict[str, str]:
    return get_auth_headers(client, "center")


def get_candidate_headers(client: TestClient) -> dict[str, str]:
    return get_auth_headers(client, "candidate")


# ── Helpers pour créer des admins via l'API /register ─────────────────────────
# Utilisé par les tests qui testent le flow complet (pas seulement le conftest)

TEST_BOOTSTRAP_TOKEN = "test-bootstrap-token-conftest"


def register_admin_via_api(client: TestClient, role: str = "admin") -> tuple[str, str]:
    """
    Crée un admin via l'endpoint /register avec le token bootstrap.
    Utilisé dans les tests qui ont besoin du flow complet (pas juste DB direct).

    Exige que auth.settings.admin_registration_token soit déjà positionné
    via le fixture set_bootstrap_token ou manuellement.
    """
    from app.routers import auth as auth_module
    prev = auth_module.settings.admin_registration_token
    auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    suffix = uuid4().hex[:8]
    email = f"api-{role}-{suffix}@coderoute.test"
    password = "StrongPass123!"
    try:
        r = client.post(
            "/api/v1/auth/register",
            headers={"X-Admin-Registration-Token": TEST_BOOTSTRAP_TOKEN},
            json={"email": email, "full_name": f"API {role}", "password": password, "role": role},
        )
        assert r.status_code == 201, f"register_admin_via_api failed: {r.json()}"
    finally:
        auth_module.settings.admin_registration_token = prev
    return email, password


@pytest.fixture(autouse=False)
def set_bootstrap_token():
    """
    Fixture optionnel : positionne ADMIN_REGISTRATION_TOKEN pour les tests
    qui créent des admins via l'API /register.
    Usage : ajouter set_bootstrap_token en paramètre du test.
    """
    from app.routers import auth as auth_module
    prev = auth_module.settings.admin_registration_token
    auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    yield TEST_BOOTSTRAP_TOKEN
    auth_module.settings.admin_registration_token = prev

"""
Fixtures partagées pour les tests E2E.
Fournit des helpers d'authentification pour les rôles super_admin, admin, center, candidate.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
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


@pytest.fixture(autouse=True)
def clean_test_questions(request):
    """
    Supprime TOUTES les questions actives après chaque test
    pour éviter la pollution de la DB partagée entre les fichiers de tests.
    Les tests qui ont besoin de questions les recrée systématiquement.
    """
    yield
    # Nettoyage agressif après chaque test : supprimer toutes les questions
    try:
        db = SessionLocal()
        from sqlalchemy import delete
        from app.models_question import Question
        db.execute(delete(Question))
        db.commit()
        db.close()
    except Exception:
        pass  # Silencieux

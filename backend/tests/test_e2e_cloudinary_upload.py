"""
Test E2E — Signature d'upload Cloudinary (upload direct navigateur).
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.core.config import get_settings
from app.models_user import User
from app.security import get_password_hash

ADMIN_EMAIL = f"cloud-{uuid.uuid4().hex[:8]}@test.gn"
ADMIN_PASS = "CloudUpload2026!"


@pytest.fixture(scope="module")
def client():
    init_db()
    db = SessionLocal()
    db.add(User(id=str(uuid.uuid4()), email=ADMIN_EMAIL, full_name="Cloud Admin",
                password_hash=get_password_hash(ADMIN_PASS), role="admin", is_active=True))
    db.commit(); db.close()
    with TestClient(app) as c:
        yield c


def _login(client) -> str:
    r = client.post("/api/v1/auth/login",
                    data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


def test_sign_upload_non_configure_503(client: TestClient, monkeypatch):
    """Sans clés Cloudinary → 503 propre (fonction désactivée)."""
    get_settings.cache_clear()
    tok = _login(client)
    r = client.post("/api/v1/questions/media/sign-upload?resource_type=image", headers=_auth(tok))
    assert r.status_code == 503
    assert "cloudinary" in r.json()["detail"].lower()


def test_sign_upload_configure(client: TestClient, monkeypatch):
    """Avec clés Cloudinary → signature valide pour image et vidéo."""
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "123456789")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret-abc-xyz")
    get_settings.cache_clear()
    try:
        tok = _login(client)
        r = client.post("/api/v1/questions/media/sign-upload?resource_type=image", headers=_auth(tok))
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["api_key"] == "123456789"
        assert d["signature"] and len(d["signature"]) == 40  # SHA-1 hex
        assert "test-cloud" in d["upload_url"] and "image" in d["upload_url"]

        r = client.post("/api/v1/questions/media/sign-upload?resource_type=video", headers=_auth(tok))
        assert r.status_code == 200 and "video" in r.json()["upload_url"]

        r = client.post("/api/v1/questions/media/sign-upload?resource_type=invalide", headers=_auth(tok))
        assert r.status_code == 422
    finally:
        get_settings.cache_clear()


def test_sign_upload_interdit_aux_candidats(client: TestClient):
    u = uuid.uuid4().hex[:6]
    cemail = f"c-{u}@test.gn"
    db = SessionLocal()
    db.add(User(id=str(uuid.uuid4()), email=cemail, full_name="Cand",
                password_hash=get_password_hash("CandPass2026!"), role="candidate", is_active=True))
    db.commit(); db.close()
    r = client.post("/api/v1/auth/login",
                    data={"username": cemail, "password": "CandPass2026!"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    tok = r.json()["access_token"]
    r = client.post("/api/v1/questions/media/sign-upload", headers=_auth(tok))
    assert r.status_code == 403

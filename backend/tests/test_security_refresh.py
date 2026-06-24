"""
Tests pour le refresh token JWT et le rate limiter persistant.
"""
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.routers import auth as auth_router
from app.security import create_access_token, create_refresh_token, decode_refresh_token


def test_refresh_token_created_on_login() -> None:
    """La réponse de login inclut access_token ET refresh_token."""
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        client.post("/api/v1/auth/register", json={
            "email": f"refresh-{suffix}@coderoute.test",
            "full_name": "Refresh Test",
            "password": "RefreshPass2026!",
            "role": "center",
        })
        resp = client.post("/api/v1/auth/login", data={
            "username": f"refresh-{suffix}@coderoute.test",
            "password": "RefreshPass2026!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["refresh_token"]) > 20


def test_refresh_endpoint_returns_new_tokens() -> None:
    """POST /auth/refresh génère un nouveau access_token valide."""
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        client.post("/api/v1/auth/register", json={
            "email": f"refresh2-{suffix}@coderoute.test",
            "full_name": "Refresh Test 2",
            "password": "RefreshPass2026!",
            "role": "admin",
        })
        login = client.post("/api/v1/auth/login", data={
            "username": f"refresh2-{suffix}@coderoute.test",
            "password": "RefreshPass2026!",
        }).json()

        refresh = client.post("/api/v1/auth/refresh", json={
            "refresh_token": login["refresh_token"],
        })
        assert refresh.status_code == 200
        data = refresh.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # Le nouveau access_token doit être utilisable
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert me.status_code == 200


def test_refresh_with_invalid_token_returns_401() -> None:
    """Un refresh token invalide retourne 401."""
    with TestClient(app) as client:
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.valid.token"})
        assert r.status_code == 401


def test_access_token_cannot_be_used_as_refresh() -> None:
    """Un access token (type='access') ne peut pas renouveler la session."""
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        client.post("/api/v1/auth/register", json={
            "email": f"no-reuse-{suffix}@coderoute.test",
            "full_name": "No Reuse",
            "password": "NoReuse2026!",
            "role": "center",
        })
        login = client.post("/api/v1/auth/login", data={
            "username": f"no-reuse-{suffix}@coderoute.test",
            "password": "NoReuse2026!",
        }).json()

        # Essayer d'utiliser l'access_token comme refresh_token
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": login["access_token"]})
        assert r.status_code == 401


def test_rate_limiter_persistent_resets_on_success() -> None:
    """Après un login réussi, le compteur de tentatives est réinitialisé."""
    suffix = uuid4().hex[:8]
    email = f"rate-reset-{suffix}@coderoute.test"
    password = "RateReset2026!"
    limiter = auth_router.login_rate_limiter
    old_max = limiter.max_attempts
    limiter.max_attempts = 3
    limiter.clear()

    try:
        with TestClient(app) as client:
            client.post("/api/v1/auth/register", json={
                "email": email, "full_name": "Rate Reset",
                "password": password, "role": "center",
            })
            # 2 tentatives échouées
            for _ in range(2):
                client.post("/api/v1/auth/login", data={"username": email, "password": "wrong"})

            # Login réussi → reset du compteur
            ok = client.post("/api/v1/auth/login", data={"username": email, "password": password})
            assert ok.status_code == 200

            # Après reset, on peut re-échouer sans être bloqué immédiatement
            r = client.post("/api/v1/auth/login", data={"username": email, "password": "wrong"})
            assert r.status_code == 401  # 401 pas 429
    finally:
        limiter.max_attempts = old_max
        limiter.clear()


def test_decode_refresh_token_rejects_access_type() -> None:
    """decode_refresh_token() refuse les tokens de type 'access'."""
    token = create_access_token("user-id-123", "admin")
    # decode_refresh_token doit retourner None pour un access token
    result = decode_refresh_token(token)
    assert result is None


def test_decode_refresh_token_accepts_refresh_type() -> None:
    """decode_refresh_token() accepte les tokens de type 'refresh'."""
    token = create_refresh_token("user-id-456")
    result = decode_refresh_token(token)
    assert result is not None
    assert result["sub"] == "user-id-456"
    assert result["type"] == "refresh"

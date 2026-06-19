from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models_audit import AuditLog
from app.routers import auth
from app import main
from app.main import app


def test_register_login_and_me() -> None:
    auth.login_rate_limiter.clear()
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        email = f"admin-{suffix}@coderoute.gn"
        password = "StrongPass123"

        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "full_name": "Admin CodeRoute",
                "password": password,
                "role": "admin",
            },
        )
        assert register_response.status_code == 201
        assert register_response.json()["role"] == "admin"

        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email


def test_user_can_change_own_password() -> None:
    auth.login_rate_limiter.clear()
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        email = f"password-{suffix}@coderoute.gn"
        old_password = "StrongPass123"
        new_password = "NewStrongPass123"
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "full_name": "Password User",
                "password": old_password,
                "role": "admin",
            },
        )
        token = client.post("/api/v1/auth/login", data={"username": email, "password": old_password}).json()["access_token"]

        change_response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": old_password, "new_password": new_password},
        )
        old_login = client.post("/api/v1/auth/login", data={"username": email, "password": old_password})
        new_login = client.post("/api/v1/auth/login", data={"username": email, "password": new_password})

    assert change_response.status_code == 204
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_login_failures_are_rate_limited_and_audited() -> None:
    auth.login_rate_limiter.clear()
    previous_attempts = auth.login_rate_limiter.max_attempts
    auth.login_rate_limiter.max_attempts = 2
    try:
        with TestClient(app) as client:
            suffix = str(uuid4())[:8]
            email = f"limited-admin-{suffix}@coderoute.gn"
            password = "StrongPass123"
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "full_name": "Limited Admin",
                    "password": password,
                    "role": "admin",
                },
            )

            first_failure = client.post("/api/v1/auth/login", data={"username": email, "password": "bad-password"})
            second_failure = client.post("/api/v1/auth/login", data={"username": email, "password": "bad-password"})
            blocked = client.post("/api/v1/auth/login", data={"username": email, "password": password})

            assert first_failure.status_code == 401
            assert second_failure.status_code == 401
            assert blocked.status_code == 429

            db = SessionLocal()
            try:
                audit_actions = db.scalars(
                    select(AuditLog.action).where(AuditLog.entity == "auth", AuditLog.details["email"].as_string() == email)
                ).all()
            finally:
                db.close()

            assert "auth.login_failed" in audit_actions
            assert "auth.login_blocked" in audit_actions
    finally:
        auth.login_rate_limiter.max_attempts = previous_attempts
        auth.login_rate_limiter.clear()


def test_security_headers_are_returned() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"


def test_trusted_host_middleware_blocks_unknown_hosts() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"host": "malicious.example"})

    assert response.status_code == 400


def test_hsts_header_is_returned_in_production() -> None:
    previous_environment = main.settings.environment
    main.settings.environment = "production"
    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        main.settings.environment = previous_environment

    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_privileged_registration_can_require_bootstrap_token() -> None:
    previous_token = auth.settings.admin_registration_token
    auth.settings.admin_registration_token = "bootstrap-test-token"
    try:
        with TestClient(app) as client:
            suffix = str(uuid4())[:8]
            payload = {
                "email": f"secure-admin-{suffix}@coderoute.gn",
                "full_name": "Secure Admin",
                "password": "StrongPass123",
                "role": "admin",
            }

            denied_response = client.post("/api/v1/auth/register", json=payload)
            assert denied_response.status_code == 403

            allowed_response = client.post(
                "/api/v1/auth/register",
                headers={"X-Admin-Registration-Token": "bootstrap-test-token"},
                json=payload,
            )
            assert allowed_response.status_code == 201
            assert allowed_response.json()["role"] == "admin"
    finally:
        auth.settings.admin_registration_token = previous_token


def test_production_privileged_registration_requires_configured_bootstrap_token() -> None:
    previous_token = auth.settings.admin_registration_token
    previous_environment = auth.settings.environment
    auth.settings.admin_registration_token = None
    auth.settings.environment = "production"
    try:
        with TestClient(app) as client:
            suffix = str(uuid4())[:8]
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"prod-admin-denied-{suffix}@coderoute.gn",
                    "full_name": "Production Admin",
                    "password": "StrongPass123",
                    "role": "admin",
                },
            )

        assert response.status_code == 403
    finally:
        auth.settings.admin_registration_token = previous_token
        auth.settings.environment = previous_environment


def test_production_privileged_registration_accepts_valid_bootstrap_token() -> None:
    previous_token = auth.settings.admin_registration_token
    previous_environment = auth.settings.environment
    auth.settings.admin_registration_token = "prod-bootstrap-token"
    auth.settings.environment = "production"
    try:
        with TestClient(app) as client:
            suffix = str(uuid4())[:8]
            response = client.post(
                "/api/v1/auth/register",
                headers={"X-Admin-Registration-Token": "prod-bootstrap-token"},
                json={
                    "email": f"prod-admin-allowed-{suffix}@coderoute.gn",
                    "full_name": "Production Admin",
                    "password": "StrongPass123",
                    "role": "super_admin",
                },
            )

        assert response.status_code == 201
        assert response.json()["role"] == "super_admin"
    finally:
        auth.settings.admin_registration_token = previous_token
        auth.settings.environment = previous_environment


def test_register_rejects_unknown_role() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"unknown-role-{suffix}@coderoute.gn",
                "full_name": "Unknown Role",
                "password": "StrongPass123",
                "role": "root",
            },
        )

    assert response.status_code == 422

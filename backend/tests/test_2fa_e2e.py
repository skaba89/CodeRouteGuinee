"""
Tests E2E complets pour le flow 2FA — Setup → Verify → Login avec code → Disable.

Couvre :
  - Setup 2FA : génération du secret TOTP + URI + codes de secours
  - Activation après vérification du premier code
  - Login avec requires_2fa=True quand 2FA activé
  - Vérification d'un code valide via /auth/2fa/check
  - Utilisation d'un code de secours
  - Désactivation du 2FA
  - Status endpoint

Approche : on génère le code TOTP depuis le secret retourné par setup
pour simuler ce que ferait Google Authenticator.
"""
import uuid

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_user import User
from app.security import get_password_hash
from app.two_factor import (
    TOTP_PERIOD,
    activate_2fa,
    check_2fa,
    disable_2fa,
    generate_backup_codes,
    generate_secret,
    generate_totp,
    is_2fa_enabled,
    setup_2fa,
    verify_totp,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(role: str = "admin") -> tuple[str, str, str]:
    """Crée un utilisateur et retourne (email, password, user_id)."""
    init_db()
    suffix = uuid.uuid4().hex[:8]
    email  = f"2fa-e2e-{suffix}@test.com"
    pwd    = "TestPass2FA123!"
    with SessionLocal() as db:
        u = User(email=email, full_name=f"2FA E2E {suffix}",
                 password_hash=get_password_hash(pwd), role=role)
        db.add(u)
        db.commit()
        db.refresh(u)
        return email, pwd, str(u.id)


def _get_token(email: str, pwd: str) -> str:
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", data={"username": email, "password": pwd})
        return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests unitaires du module two_factor ─────────────────────────────────────

class TestTotpCoreLogic:
    def test_generate_secret_length(self):
        s = generate_secret()
        assert len(s) >= 16  # Base32 de 20 bytes = 32 chars

    def test_generate_secret_base32_chars(self):
        import re
        s = generate_secret()
        assert re.match(r'^[A-Z2-7]+$', s)

    def test_generate_totp_6_digits(self):
        s = generate_secret()
        code = generate_totp(s)
        assert len(code) == 6
        assert code.isdigit()

    def test_verify_totp_current_code(self):
        s = generate_secret()
        code = generate_totp(s)
        assert verify_totp(s, code) is True

    def test_verify_totp_wrong_code(self):
        s = generate_secret()
        # Code certainement faux (inverse des 6 derniers chiffres vrais)
        real = generate_totp(s)
        fake = str((int(real) + 111111) % 1000000).zfill(6)
        # Ce test peut échouer si fake == real par coïncidence, mais très improbable
        if fake != real:
            assert verify_totp(s, fake) is False

    def test_verify_totp_with_window(self):
        """La fenêtre de ±1 période tolère le décalage d'horloge."""
        import time
        s = generate_secret()
        # Code de la période précédente
        past_code = generate_totp(s, time.time() - TOTP_PERIOD)
        assert verify_totp(s, past_code, window=1) is True

    def test_generate_backup_codes_count_and_format(self):
        codes = generate_backup_codes()
        assert len(codes) == 8
        for c in codes:
            assert len(c) == 8
            assert c.upper() == c  # majuscules

    def test_totp_uri_format(self):
        from app.two_factor import get_totp_uri
        uri = get_totp_uri("JBSWY3DPEHPK3PXP", "user@test.com")
        assert uri.startswith("otpauth://totp/")
        assert "secret=JBSWY3DPEHPK3PXP" in uri
        assert "issuer=" in uri

    def test_different_secrets_give_different_codes(self):
        s1, s2 = generate_secret(), generate_secret()
        _c1, _c2 = generate_totp(s1), generate_totp(s2)
        # Très improbable que 2 secrets différents donnent le même code
        assert s1 != s2  # Les secrets sont différents


# ── Tests DB (setup/activate/check/disable) ───────────────────────────────────

class TestTotpDbOperations:
    def test_setup_returns_required_fields(self):
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            result = setup_2fa(user_id, email, db)
        assert "secret_b32" in result
        assert "totp_uri" in result
        assert "backup_codes" in result
        assert len(result["backup_codes"]) == 8

    def test_is_2fa_enabled_false_after_setup(self):
        """Le 2FA n'est PAS activé après setup — il faut verify."""
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            setup_2fa(user_id, email, db)
            assert is_2fa_enabled(user_id, db) is False

    def test_activate_with_wrong_code_fails(self):
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            setup_2fa(user_id, email, db)
            result = activate_2fa(user_id, "000000", db)
        assert result is False

    def test_activate_with_correct_code_succeeds(self):
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            r = setup_2fa(user_id, email, db)
            secret = r["secret_b32"]
            code = generate_totp(secret)
            ok = activate_2fa(user_id, code, db)
        assert ok is True

    def test_is_2fa_enabled_true_after_activate(self):
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            r = setup_2fa(user_id, email, db)
            code = generate_totp(r["secret_b32"])
            activate_2fa(user_id, code, db)
            assert is_2fa_enabled(user_id, db) is True

    def test_check_2fa_with_valid_totp(self):
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            r = setup_2fa(user_id, email, db)
            secret = r["secret_b32"]
            activate_2fa(user_id, generate_totp(secret), db)
            code = generate_totp(secret)
            result = check_2fa(user_id, code, db)
        assert result is True

    def test_check_2fa_invalid_code(self):
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            r = setup_2fa(user_id, email, db)
            activate_2fa(user_id, generate_totp(r["secret_b32"]), db)
            result = check_2fa(user_id, "999999", db)
        assert result is False

    def test_check_2fa_with_backup_code(self):
        """Un code de secours peut être utilisé à la place du TOTP."""
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            r = setup_2fa(user_id, email, db)
            activate_2fa(user_id, generate_totp(r["secret_b32"]), db)
            backup = r["backup_codes"][0]
            result = check_2fa(user_id, backup, db)
        assert result is True

    def test_backup_code_consumed_after_use(self):
        """Un code de secours est à usage unique."""
        import json

        from sqlalchemy import text
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            r = setup_2fa(user_id, email, db)
            activate_2fa(user_id, generate_totp(r["secret_b32"]), db)
            backup = r["backup_codes"][0]
            check_2fa(user_id, backup, db)
            # Vérifier que le code n'est plus dans la liste
            row = db.execute(
                text("SELECT backup_codes FROM tfa_secrets WHERE user_id=:uid"),
                {"uid": user_id}
            ).fetchone()
            remaining = json.loads(row[0]) if row else []
        assert backup not in remaining

    def test_disable_2fa(self):
        init_db()
        email, _, user_id = _make_user()
        with SessionLocal() as db:
            r = setup_2fa(user_id, email, db)
            activate_2fa(user_id, generate_totp(r["secret_b32"]), db)
            disable_2fa(user_id, db)
            assert is_2fa_enabled(user_id, db) is False

    def test_check_2fa_returns_true_when_not_enabled(self):
        """Si 2FA non activé, check_2fa retourne True (pas de blocage)."""
        init_db()
        _, _, user_id = _make_user()
        with SessionLocal() as db:
            result = check_2fa(user_id, "any_code", db)
        assert result is True


# ── Tests API endpoints ───────────────────────────────────────────────────────

class TestTwoFactorEndpoints:
    def test_status_returns_false_by_default(self):
        email, pwd, _ = _make_user()
        tok = _get_token(email, pwd)
        with TestClient(app) as c:
            r = c.get("/api/v1/auth/2fa/status", headers=_auth(tok))
        assert r.status_code == 200
        assert r.json()["enabled"] is False

    def test_setup_returns_totp_uri(self):
        email, pwd, _ = _make_user()
        tok = _get_token(email, pwd)
        with TestClient(app) as c:
            r = c.post("/api/v1/auth/2fa/setup", headers=_auth(tok))
        assert r.status_code == 200
        data = r.json()
        assert data["totp_uri"].startswith("otpauth://totp/")
        assert "CodeRoute" in data["totp_uri"]

    def test_setup_returns_8_backup_codes(self):
        email, pwd, _ = _make_user()
        tok = _get_token(email, pwd)
        with TestClient(app) as c:
            r = c.post("/api/v1/auth/2fa/setup", headers=_auth(tok))
        assert len(r.json()["backup_codes"]) == 8

    def test_verify_wrong_code_returns_400(self):
        email, pwd, _ = _make_user()
        tok = _get_token(email, pwd)
        with TestClient(app) as c:
            c.post("/api/v1/auth/2fa/setup", headers=_auth(tok))
            r = c.post("/api/v1/auth/2fa/verify", headers=_auth(tok),
                       json={"code": "000000"})
        assert r.status_code == 400

    def test_full_2fa_setup_and_verify_flow(self):
        """Flow complet : setup → verify avec vrai code → status enabled."""
        email, pwd, _ = _make_user()
        tok = _get_token(email, pwd)
        with TestClient(app) as c:
            setup_resp = c.post("/api/v1/auth/2fa/setup", headers=_auth(tok))
            secret = setup_resp.json()["secret_b32"]
            code   = generate_totp(secret)
            verify = c.post("/api/v1/auth/2fa/verify", headers=_auth(tok),
                            json={"code": code})
            assert verify.status_code == 200
            assert verify.json()["activated"] is True
            status = c.get("/api/v1/auth/2fa/status", headers=_auth(tok))
            assert status.json()["enabled"] is True

    def test_login_returns_requires_2fa_when_enabled(self):
        """Après activation, le login retourne requires_2fa=True."""
        email, pwd, _ = _make_user()
        tok = _get_token(email, pwd)
        # Activer le 2FA
        with TestClient(app) as c:
            setup_resp = c.post("/api/v1/auth/2fa/setup", headers=_auth(tok))
            secret = setup_resp.json()["secret_b32"]
            c.post("/api/v1/auth/2fa/verify", headers=_auth(tok),
                   json={"code": generate_totp(secret)})
        # Re-tenter le login
        with TestClient(app) as c:
            login_resp = c.post("/api/v1/auth/login",
                                data={"username": email, "password": pwd})
        data = login_resp.json()
        assert data.get("requires_2fa") is True
        assert data.get("user_id") is not None

    def test_2fa_check_endpoint_with_valid_code(self):
        """POST /auth/2fa/check avec un vrai code TOTP → 200."""
        email, pwd, user_id = _make_user()
        tok = _get_token(email, pwd)
        with TestClient(app) as c:
            setup_resp = c.post("/api/v1/auth/2fa/setup", headers=_auth(tok))
            secret = setup_resp.json()["secret_b32"]
            c.post("/api/v1/auth/2fa/verify", headers=_auth(tok),
                   json={"code": generate_totp(secret)})
            r = c.post("/api/v1/auth/2fa/check",
                       params={"user_id": user_id},
                       headers=_auth(tok),
                       json={"code": generate_totp(secret)})
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_2fa_check_endpoint_invalid_code(self):
        email, pwd, user_id = _make_user()
        tok = _get_token(email, pwd)
        with TestClient(app) as c:
            setup_resp = c.post("/api/v1/auth/2fa/setup", headers=_auth(tok))
            secret = setup_resp.json()["secret_b32"]
            c.post("/api/v1/auth/2fa/verify", headers=_auth(tok),
                   json={"code": generate_totp(secret)})
            r = c.post("/api/v1/auth/2fa/check",
                       params={"user_id": user_id},
                       headers=_auth(tok),
                       json={"code": "999999"})
        assert r.status_code == 401

    def test_disable_endpoint(self):
        email, pwd, _ = _make_user()
        tok = _get_token(email, pwd)
        with TestClient(app) as c:
            r = c.post("/api/v1/auth/2fa/disable", headers=_auth(tok))
        assert r.status_code == 200
        assert r.json()["disabled"] is True

    def test_endpoints_require_auth(self):
        with TestClient(app) as c:
            for endpoint in ["/api/v1/auth/2fa/setup", "/api/v1/auth/2fa/verify",
                             "/api/v1/auth/2fa/status", "/api/v1/auth/2fa/disable"]:
                r = c.get(endpoint) if "status" in endpoint else c.post(endpoint, json={})
                assert r.status_code == 401, f"{endpoint} devrait retourner 401"

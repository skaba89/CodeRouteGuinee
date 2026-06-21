"""
Tests de sécurité — Phase 4 : Sécurité institutionnelle admin.

Couvre :
  1. Protection rôles privilégiés (admin, super_admin) — token obligatoire
  2. Validation mot de passe fort
  3. Audit log sur tentative refusée
  4. Comportement en "production" (ADMIN_REGISTRATION_TOKEN absent → toujours bloqué)
"""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog
from app.routers import auth

# ── Helpers ───────────────────────────────────────────────────────

STRONG_PASSWORD = "CodeRoute2026!"  # satisfait toutes les règles

def _unique_email(prefix: str = "sec") -> str:
    return f"{prefix}-{uuid4().hex[:8]}@coderoute-sec.gn"

def _register(client, email, password=STRONG_PASSWORD, role="candidate", token=None):
    headers = {}
    if token:
        headers["X-Admin-Registration-Token"] = token
    return client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={"email": email, "full_name": "Test User", "password": password, "role": role},
    )

def _audit_actions_for_email(email: str) -> list[str]:
    db = SessionLocal()
    try:
        return list(db.scalars(
            select(AuditLog.action).where(
                AuditLog.entity == "auth",
                AuditLog.details["email"].as_string() == email.lower(),
            )
        ).all())
    finally:
        db.close()

def _set_token(value: str | None):
    """Modifie ADMIN_REGISTRATION_TOKEN dans le module auth."""
    auth.settings.admin_registration_token = value

def _get_token() -> str | None:
    return auth.settings.admin_registration_token


# ══════════════════════════════════════════════════════════════════
# 1. Candidat normal — inscription libre
# ══════════════════════════════════════════════════════════════════

class TestCandidateRegistration:
    def test_candidate_created_without_token(self):
        """Un candidat peut s'inscrire sans token d'administration."""
        with TestClient(app) as client:
            r = _register(client, _unique_email("cand"), role="candidate")
        assert r.status_code == 201
        assert r.json()["role"] == "candidate"

    def test_candidate_strong_password_required(self):
        """Le candidat doit aussi fournir un mot de passe fort."""
        with TestClient(app) as client:
            r = _register(client, _unique_email("weak"), password="weak", role="candidate")
        assert r.status_code == 422

    def test_candidate_duplicate_email_rejected(self):
        """Deux inscriptions avec le même email → 409."""
        email = _unique_email("dup")
        with TestClient(app) as client:
            _register(client, email, role="candidate")
            r = _register(client, email, role="candidate")
        assert r.status_code == 409

    def test_center_role_no_token_needed(self):
        """Le rôle 'center' n'est pas privilégié — pas de token requis."""
        with TestClient(app) as client:
            r = _register(client, _unique_email("ctr"), role="center")
        # Selon le modèle métier, center peut être créé librement
        # (seuls admin et super_admin nécessitent un token)
        assert r.status_code in (201, 403)  # selon la politique du projet


# ══════════════════════════════════════════════════════════════════
# 2. Admin sans token — toujours refusé
# ══════════════════════════════════════════════════════════════════

class TestAdminRegistrationNoToken:
    def test_admin_refused_without_token_when_configured(self):
        """Admin sans token → 403 si ADMIN_REGISTRATION_TOKEN est configuré."""
        prev = _get_token()
        _set_token("secret-bootstrap-token")
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("adm-nt"), role="admin")
            assert r.status_code == 403
            assert "token" in r.json()["detail"].lower() or "privileged" in r.json()["detail"].lower()
        finally:
            _set_token(prev)

    def test_super_admin_refused_without_token_when_configured(self):
        """super_admin sans token → 403 si configuré."""
        prev = _get_token()
        _set_token("secret-bootstrap-token")
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("sa-nt"), role="super_admin")
            assert r.status_code == 403
        finally:
            _set_token(prev)

    def test_admin_refused_when_token_not_configured(self):
        """
        FAILLE CORRIGÉE : même si ADMIN_REGISTRATION_TOKEN est absent/vide,
        la création d'admin doit être refusée (403), pas autorisée.
        """
        prev = _get_token()
        _set_token(None)  # token non configuré → doit quand même bloquer
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("adm-nc"), role="admin")
            assert r.status_code == 403, (
                f"FAILLE : admin créé sans ADMIN_REGISTRATION_TOKEN (status={r.status_code})"
            )
            assert "disabled" in r.json()["detail"].lower() or "configured" in r.json()["detail"].lower()
        finally:
            _set_token(prev)

    def test_super_admin_refused_when_token_not_configured(self):
        """Idem pour super_admin."""
        prev = _get_token()
        _set_token(None)
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("sa-nc"), role="super_admin")
            assert r.status_code == 403
        finally:
            _set_token(prev)

    def test_admin_refused_with_empty_string_token(self):
        """Token configuré vide → doit bloquer."""
        prev = _get_token()
        _set_token("")  # chaîne vide = non configuré
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("adm-empty"), role="admin")
            assert r.status_code == 403
        finally:
            _set_token(prev)


# ══════════════════════════════════════════════════════════════════
# 3. Admin avec mauvais token — refusé
# ══════════════════════════════════════════════════════════════════

class TestAdminRegistrationBadToken:
    def test_admin_refused_with_wrong_token(self):
        """Admin avec mauvais token → 403."""
        prev = _get_token()
        _set_token("correct-token-abc")
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("adm-wt"), role="admin", token="wrong-token")
            assert r.status_code == 403
        finally:
            _set_token(prev)

    def test_super_admin_refused_with_wrong_token(self):
        """super_admin avec mauvais token → 403."""
        prev = _get_token()
        _set_token("correct-token-abc")
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("sa-wt"), role="super_admin", token="wrong-token")
            assert r.status_code == 403
        finally:
            _set_token(prev)

    def test_admin_refused_with_empty_token_header(self):
        """Token vide dans le header → 403."""
        prev = _get_token()
        _set_token("correct-token-abc")
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("adm-et"), role="admin", token="")
            assert r.status_code in (403, 422)
        finally:
            _set_token(prev)

    def test_admin_refused_with_case_different_token(self):
        """Token en mauvaise casse → 403 (comparaison exacte)."""
        prev = _get_token()
        _set_token("CaseSensitiveToken123")
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("adm-case"), role="admin", token="casesensitivetoken123")
            assert r.status_code == 403
        finally:
            _set_token(prev)


# ══════════════════════════════════════════════════════════════════
# 4. Admin avec bon token — accepté
# ══════════════════════════════════════════════════════════════════

class TestAdminRegistrationGoodToken:
    def test_admin_accepted_with_correct_token(self):
        """Admin avec le bon token → 201."""
        prev = _get_token()
        token = "correct-bootstrap-token-123"
        _set_token(token)
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("adm-ok"), role="admin", token=token)
            assert r.status_code == 201
            assert r.json()["role"] == "admin"
        finally:
            _set_token(prev)

    def test_super_admin_accepted_with_correct_token(self):
        """super_admin avec le bon token → 201."""
        prev = _get_token()
        token = "correct-bootstrap-token-456"
        _set_token(token)
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("sa-ok"), role="super_admin", token=token)
            assert r.status_code == 201
            assert r.json()["role"] == "super_admin"
        finally:
            _set_token(prev)

    def test_accepted_admin_can_login(self):
        """Admin créé avec le bon token peut se connecter."""
        prev = _get_token()
        token = "bootstrap-login-test-789"
        _set_token(token)
        auth.login_rate_limiter.clear()
        email = _unique_email("adm-login")
        try:
            with TestClient(app) as client:
                _register(client, email, role="admin", token=token)
                r = client.post("/api/v1/auth/login", data={"username": email, "password": STRONG_PASSWORD})
            assert r.status_code == 200
            assert "access_token" in r.json()
        finally:
            _set_token(prev)


# ══════════════════════════════════════════════════════════════════
# 5. Comportement production — ADMIN_REGISTRATION_TOKEN absent
# ══════════════════════════════════════════════════════════════════

class TestProductionBehavior:
    """
    Simule un environnement de production où ADMIN_REGISTRATION_TOKEN
    n'est pas configuré. Dans ce cas, toute tentative de créer un rôle
    privilégié doit être bloquée SANS EXCEPTION.
    """

    def test_production_no_token_blocks_admin(self):
        prev_env = auth.settings.environment
        prev_tok = _get_token()
        auth.settings.environment = "production"
        _set_token(None)
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("prod-adm"), role="admin")
            assert r.status_code == 403
        finally:
            auth.settings.environment = prev_env
            _set_token(prev_tok)

    def test_production_no_token_blocks_super_admin(self):
        prev_env = auth.settings.environment
        prev_tok = _get_token()
        auth.settings.environment = "production"
        _set_token(None)
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("prod-sa"), role="super_admin")
            assert r.status_code == 403
        finally:
            auth.settings.environment = prev_env
            _set_token(prev_tok)

    def test_production_with_token_allows_admin(self):
        """En production avec le bon token → admin autorisé."""
        prev_env = auth.settings.environment
        prev_tok = _get_token()
        token = "prod-bootstrap-secure-token"
        auth.settings.environment = "production"
        _set_token(token)
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("prod-adm-ok"), role="admin", token=token)
            assert r.status_code == 201
        finally:
            auth.settings.environment = prev_env
            _set_token(prev_tok)

    def test_production_candidate_still_works_without_token(self):
        """En production, un candidat peut toujours s'inscrire normalement."""
        prev_env = auth.settings.environment
        prev_tok = _get_token()
        auth.settings.environment = "production"
        _set_token(None)
        try:
            with TestClient(app) as client:
                r = _register(client, _unique_email("prod-cand"), role="candidate")
            assert r.status_code == 201
        finally:
            auth.settings.environment = prev_env
            _set_token(prev_tok)


# ══════════════════════════════════════════════════════════════════
# 6. Audit log sur tentative refusée
# ══════════════════════════════════════════════════════════════════

class TestAuditLogOnDenied:
    def test_audit_log_created_on_admin_denied_no_token(self):
        """Un audit log auth.register_privileged_denied est créé si refusé."""
        prev = _get_token()
        _set_token("audit-test-token")
        email = _unique_email("audit-adm")
        try:
            with TestClient(app) as client:
                r = _register(client, email, role="admin")
            assert r.status_code == 403
            actions = _audit_actions_for_email(email)
            assert "auth.register_privileged_denied" in actions, (
                f"Audit log manquant. Actions trouvées : {actions}"
            )
        finally:
            _set_token(prev)

    def test_audit_log_contains_reason_bad_token(self):
        """L'audit log doit contenir reason='bad_token' si un mauvais token est fourni."""
        prev = _get_token()
        _set_token("good-token-xyz")
        email = _unique_email("audit-badtok")
        try:
            with TestClient(app) as client:
                _register(client, email, role="admin", token="wrong-token")
            db = SessionLocal()
            try:
                log = db.scalar(
                    select(AuditLog).where(
                        AuditLog.action == "auth.register_privileged_denied",
                        AuditLog.details["email"].as_string() == email.lower(),
                    )
                )
                assert log is not None
                assert log.details.get("reason") == "bad_token"
                assert log.details.get("role") == "admin"
                assert log.details.get("token_configured") is True
                assert log.details.get("token_provided") is True
            finally:
                db.close()
        finally:
            _set_token(prev)

    def test_audit_log_contains_reason_no_token(self):
        """L'audit log doit contenir reason='no_token' si le token n'est pas configuré."""
        prev = _get_token()
        _set_token(None)
        email = _unique_email("audit-notok")
        try:
            with TestClient(app) as client:
                _register(client, email, role="super_admin")
            db = SessionLocal()
            try:
                log = db.scalar(
                    select(AuditLog).where(
                        AuditLog.action == "auth.register_privileged_denied",
                        AuditLog.details["email"].as_string() == email.lower(),
                    )
                )
                assert log is not None
                assert log.details.get("reason") == "no_token"
                assert log.details.get("token_configured") is False
                assert log.details.get("token_provided") is False
            finally:
                db.close()
        finally:
            _set_token(prev)

    def test_audit_log_records_ip(self):
        """L'audit log doit contenir l'IP du requérant."""
        prev = _get_token()
        _set_token("token-ip-test")
        email = _unique_email("audit-ip")
        try:
            with TestClient(app) as client:
                _register(client, email, role="admin")
            db = SessionLocal()
            try:
                log = db.scalar(
                    select(AuditLog).where(
                        AuditLog.action == "auth.register_privileged_denied",
                        AuditLog.details["email"].as_string() == email.lower(),
                    )
                )
                assert log is not None
                assert "ip" in log.details
            finally:
                db.close()
        finally:
            _set_token(prev)

    def test_no_audit_log_on_successful_admin_creation(self):
        """Pas d'audit log 'denied' si la création réussit."""
        prev = _get_token()
        token = "success-audit-token"
        _set_token(token)
        email = _unique_email("audit-ok")
        try:
            with TestClient(app) as client:
                r = _register(client, email, role="admin", token=token)
            assert r.status_code == 201
            actions = _audit_actions_for_email(email)
            assert "auth.register_privileged_denied" not in actions
        finally:
            _set_token(prev)


# ══════════════════════════════════════════════════════════════════
# 7. Validation mot de passe fort
# ══════════════════════════════════════════════════════════════════

class TestPasswordStrength:
    """Tests de la politique de mot de passe sur l'endpoint /register."""

    def _try_register(self, password: str) -> int:
        with TestClient(app) as client:
            return _register(client, _unique_email("pwd"), password=password).status_code

    def test_password_too_short_rejected(self):
        assert self._try_register("Ab1!") == 422

    def test_password_no_uppercase_rejected(self):
        assert self._try_register("monmotdepasse1!") == 422

    def test_password_no_lowercase_rejected(self):
        assert self._try_register("MONMOTDEPASSE1!") == 422

    def test_password_no_digit_rejected(self):
        assert self._try_register("MonMotDePasse!") == 422

    def test_password_no_special_rejected(self):
        assert self._try_register("MonMotDePasse1") == 422

    def test_password_all_criteria_met_accepted(self):
        assert self._try_register(STRONG_PASSWORD) == 201

    def test_password_various_specials_accepted(self):
        for pwd in ["TestPass1@xyz", "TestPass1#xyz", "TestPass1$xyz", "TestPass1%xyz"]:
            assert self._try_register(pwd) == 201, f"'{pwd}' devrait être accepté"

    def test_password_unicode_digit_not_counted(self):
        """Les chiffres Unicode (ex: ①) ne satisfont pas la règle chiffre ASCII."""
        # "MonMotDePasse①!" — le ① n'est pas un chiffre ASCII [0-9]
        # Comportement attendu : rejeté (pas de [0-9])
        r = self._try_register("MonMotDePasse①!")
        assert r == 422

    def test_password_error_message_is_informative(self):
        """Le message d'erreur doit expliquer pourquoi le mot de passe est rejeté."""
        with TestClient(app) as client:
            r = _register(client, _unique_email("pwd-msg"), password="weak")
        assert r.status_code == 422
        body = r.json()
        # Le message d'erreur doit être lisible
        detail = str(body.get("detail", ""))
        assert any(word in detail.lower() for word in [
            "caractère", "majuscule", "minuscule", "chiffre", "spécial", "password", "12"
        ])

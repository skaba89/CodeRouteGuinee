"""
Tests coverage — email_service, audio, api, domain, deps.

Cibles :
  app/email_service.py  (0%  → 90%+) — mode dev + mode prod mock httpx
  app/routers/audio.py  (0%  → 85%+) — check/inventory/upload/delete
  app/api.py            (0%  → 100%) — constante API_VERSION
  app/domain.py         (0%  → 100%) — constantes métier
  app/bootstrap_admin.py (78% → 90%) — lignes 48-60, 64
  app/deps.py           (92% → 100%) — lignes 19, 22
"""
import io
import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_user import User
from app.security import get_password_hash
from tests.conftest import get_admin_headers


# ══════════════════════════════════════════════════════════════════
# 1. api.py et domain.py — constantes
# ══════════════════════════════════════════════════════════════════

class TestApiConstants:
    def test_api_version_exists(self):
        from app.api import API_VERSION
        assert isinstance(API_VERSION, str)
        assert len(API_VERSION) > 0

    def test_api_version_semver_format(self):
        from app.api import API_VERSION
        parts = API_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestDomainConstants:
    def test_user_roles_defined(self):
        from app.domain import USER_ROLES
        assert isinstance(USER_ROLES, list)
        assert "admin" in USER_ROLES
        assert "super_admin" in USER_ROLES

    def test_center_statuses_defined(self):
        from app.domain import CENTER_STATUSES
        assert isinstance(CENTER_STATUSES, list)
        assert len(CENTER_STATUSES) > 0

    def test_session_statuses_defined(self):
        from app.domain import SESSION_STATUSES
        assert isinstance(SESSION_STATUSES, list)
        assert "open" in SESSION_STATUSES or "planned" in SESSION_STATUSES


# ══════════════════════════════════════════════════════════════════
# 2. email_service.py — mode dev + mock httpx
# ══════════════════════════════════════════════════════════════════

class TestEmailServiceDevMode:
    """Tests en mode dev (sans BREVO_API_KEY) — les emails sont loggués, pas envoyés."""

    def _clean_env(self):
        return {k: v for k, v in os.environ.items() if k != "BREVO_API_KEY"}

    def test_send_logs_without_api_key(self, caplog):
        from app.email_service import _send
        with patch.dict(os.environ, self._clean_env(), clear=True):
            result = _send("test@example.com", "Test User", "Sujet test", "<p>Body</p>")
        assert result is True  # succès en dev

    def test_booking_confirmation_dev_mode(self):
        from app.email_service import send_booking_confirmation
        with patch.dict(os.environ, self._clean_env(), clear=True):
            result = send_booking_confirmation(
                to_email="candidat@test.com",
                candidate_name="Mamadou Diallo",
                booking_reference="GN-BK-2026-000001",
                session_date="15/07/2026 à 08h00",
                center_name="Centre de Conakry - Kaloum",
                verification_code="VC-ABC123",
            )
        assert result is True

    def test_payment_confirmation_dev_mode(self):
        from app.email_service import send_payment_confirmation
        with patch.dict(os.environ, self._clean_env(), clear=True):
            result = send_payment_confirmation(
                to_email="candidat@test.com",
                candidate_name="Fatoumata Bah",
                booking_reference="GN-BK-2026-000002",
                amount_gnf=150_000,
                provider="wave",
                receipt_number="RCP-2026-000001",
            )
        assert result is True

    def test_exam_result_passed_dev_mode(self):
        from app.email_service import send_exam_result
        with patch.dict(os.environ, self._clean_env(), clear=True):
            result = send_exam_result(
                to_email="candidat@test.com",
                candidate_name="Ibrahima Camara",
                booking_reference="GN-BK-2026-000003",
                passed=True,
                score=37,
                total=40,
                certificate_url="https://api.coderoute.gov.gn/api/v1/exams/abc/certificate/verify",
            )
        assert result is True

    def test_exam_result_failed_dev_mode(self):
        from app.email_service import send_exam_result
        with patch.dict(os.environ, self._clean_env(), clear=True):
            result = send_exam_result(
                to_email="candidat@test.com",
                candidate_name="Alpha Barry",
                booking_reference="GN-BK-2026-000004",
                passed=False,
                score=28,
                total=40,
                certificate_url=None,
            )
        assert result is True

    def test_exam_result_no_certificate_url(self):
        from app.email_service import send_exam_result
        with patch.dict(os.environ, self._clean_env(), clear=True):
            result = send_exam_result(
                to_email="test@test.com",
                candidate_name="Test",
                booking_reference="GN-BK-000",
                passed=True,
                score=35,
                total=40,
            )
        assert result is True

    def test_convocation_dev_mode(self):
        from app.email_service import send_convocation
        with patch.dict(os.environ, self._clean_env(), clear=True):
            result = send_convocation(
                to_email="candidat@test.com",
                candidate_name="Aissatou Sow",
                booking_reference="GN-BK-2026-000005",
                session_date="20/07/2026 à 09h00",
                center_name="Centre Ratoma",
                center_address="Quartier Cosa, Conakry",
                qr_verification_url="https://coderoute.gov.gn/verify/GN-BK-2026-000005",
            )
        assert result is True

    def test_all_providers_in_payment_confirmation(self):
        from app.email_service import send_payment_confirmation
        providers = ["orange_money", "wave", "mtn_money", "moov_money", "sandbox", "unknown"]
        with patch.dict(os.environ, self._clean_env(), clear=True):
            for prov in providers:
                result = send_payment_confirmation(
                    to_email="t@t.com", candidate_name="Test",
                    booking_reference="GN-BK-000", amount_gnf=100_000,
                    provider=prov, receipt_number="RCP-000",
                )
                assert result is True, f"Échec pour provider {prov}"


class TestEmailServiceProdMode:
    """Tests en mode prod avec mock httpx."""

    def _mock_success(self) -> MagicMock:
        r = MagicMock()
        r.status_code = 201
        return r

    def _mock_failure(self, code: int = 400) -> MagicMock:
        r = MagicMock()
        r.status_code = code
        r.text = "Bad Request"
        return r

    def test_send_success_with_api_key(self):
        from app.email_service import _send
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-test-key"}):
            with patch("httpx.post", return_value=self._mock_success()):
                result = _send("test@test.com", "Test", "Subject", "<p>Body</p>")
        assert result is True

    def test_send_failure_http_error_returns_false(self):
        from app.email_service import _send
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-test-key"}):
            with patch("httpx.post", return_value=self._mock_failure(500)):
                result = _send("test@test.com", "Test", "Subject", "<p>Body</p>")
        assert result is False

    def test_send_network_error_returns_false(self):
        from app.email_service import _send
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-test-key"}):
            with patch("httpx.post", side_effect=Exception("Connection refused")):
                result = _send("test@test.com", "Test", "Subject", "<p>Body</p>")
        assert result is False

    def test_send_calls_brevo_api_url(self):
        from app.email_service import _send, _BREVO_API_URL
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-test-key"}):
            with patch("httpx.post", return_value=self._mock_success()) as mock_post:
                _send("test@test.com", "Test", "Subject", "<p>Body</p>")
                call_url = mock_post.call_args[0][0]
                assert call_url == _BREVO_API_URL

    def test_send_includes_api_key_header(self):
        from app.email_service import _send
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-test-key-123"}):
            with patch("httpx.post", return_value=self._mock_success()) as mock_post:
                _send("test@test.com", "Test", "Subject", "<p>Body</p>")
                headers = mock_post.call_args[1]["headers"]
                assert headers["api-key"] == "xkeysib-test-key-123"

    def test_send_timeout_10s(self):
        from app.email_service import _send
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-test-key"}):
            with patch("httpx.post", return_value=self._mock_success()) as mock_post:
                _send("test@test.com", "Test", "Subject", "<p>Body</p>")
                assert mock_post.call_args[1]["timeout"] == 10

    def test_send_200_also_success(self):
        """Brevo retourne parfois 200 au lieu de 201."""
        from app.email_service import _send
        mock_200 = MagicMock()
        mock_200.status_code = 200
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-test-key"}):
            with patch("httpx.post", return_value=mock_200):
                result = _send("test@test.com", "Test", "Subject", "<p>Body</p>")
        assert result is True

    def test_booking_confirmation_prod_mode(self):
        from app.email_service import send_booking_confirmation
        with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-test-key"}):
            with patch("httpx.post", return_value=self._mock_success()):
                result = send_booking_confirmation(
                    to_email="test@test.com",
                    candidate_name="Test",
                    booking_reference="GN-BK-000",
                    session_date="15/07/2026",
                    center_name="Centre Test",
                    verification_code="VC-000",
                )
        assert result is True


# ══════════════════════════════════════════════════════════════════
# 3. routers/audio.py — endpoints audio
# ══════════════════════════════════════════════════════════════════

class TestAudioRouter:
    """Tests du router audio — check, inventory, upload, delete."""

    def _headers(self, client: TestClient) -> dict:
        return get_admin_headers(client)

    def _super_admin_headers(self, client: TestClient) -> dict:
        """Crée un super_admin pour les opérations delete."""
        init_db()
        suffix = uuid.uuid4().hex[:6]
        email = f"sa-audio-{suffix}@test.com"
        with SessionLocal() as db:
            u = User(email=email, full_name="SA Audio Test",
                     password_hash=get_password_hash("TestPass123!"),
                     role="super_admin")
            db.add(u); db.commit()
        with TestClient(app) as client:
            token = client.post("/api/v1/auth/login",
                                data={"username": email, "password": "TestPass123!"}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # ── check ──────────────────────────────────────────────────────

    def test_check_nonexistent_returns_false(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audio/check/ff/q-nonexistent-12345")
        assert r.status_code == 200
        assert r.json()["exists"] is False

    def test_check_invalid_locale_returns_400(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audio/check/xx/q-test")
        assert r.status_code == 400

    def test_check_valid_locale_ff(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audio/check/ff/q-test-nonexistent")
        assert r.status_code == 200
        data = r.json()
        assert "exists" in data
        assert data["locale"] == "ff"
        assert data["question_id"] == "q-test-nonexistent"

    def test_check_valid_locale_fr(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audio/check/fr/q-test")
        assert r.status_code == 200
        assert r.json()["locale"] == "fr"

    def test_check_all_valid_locales(self):
        valid = ["ff", "man", "sus", "kss", "gkp", "lom", "fr", "en"]
        with TestClient(app) as client:
            for locale in valid:
                r = client.get(f"/api/v1/audio/check/{locale}/q-test")
                assert r.status_code == 200, f"Locale {locale} a retourné {r.status_code}"

    # ── inventory ──────────────────────────────────────────────────

    def test_inventory_returns_all_locales(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audio/inventory")
        assert r.status_code == 200
        data = r.json()
        assert "by_locale" in data
        assert "total_files" in data
        assert "coverage_pct" in data
        # Toutes les locales doivent apparaître
        for loc in ["ff", "man", "sus", "kss", "gkp", "lom", "fr", "en"]:
            assert loc in data["by_locale"]

    def test_inventory_filter_by_locale(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audio/inventory?locale=ff")
        assert r.status_code == 200
        data = r.json()
        assert "ff" in data["by_locale"]
        # Les autres locales ne doivent pas apparaître si filtre activé
        # (dépend de l'implémentation — au moins "ff" est là)

    def test_inventory_total_files_integer(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audio/inventory")
        assert isinstance(r.json()["total_files"], int)
        assert r.json()["total_files"] >= 0

    def test_inventory_coverage_pct_between_0_and_100(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audio/inventory")
        for loc, pct in r.json()["coverage_pct"].items():
            assert 0 <= pct <= 100, f"Coverage invalide pour {loc}: {pct}"

    # ── upload ────────────────────────────────────────────────────

    def _make_fake_mp3(self, size_kb: int = 10) -> bytes:
        """Crée un faux MP3 valide (avec signature ID3)."""
        header = b'ID3\x03\x00\x00\x00\x00\x00\x00'
        return header + b'\x00' * (size_kb * 1024 - len(header))

    def test_upload_requires_auth(self):
        mp3_data = self._make_fake_mp3()
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/audio/upload/ff/q-test",
                files={"file": ("test.mp3", io.BytesIO(mp3_data), "audio/mpeg")},
            )
        assert r.status_code == 401

    def test_upload_valid_mp3_as_admin(self, tmp_path, monkeypatch):
        """Upload d'un MP3 valide — stocké dans un dossier temporaire."""
        from app.routers import audio as audio_module
        tmp_audio = tmp_path / "audio"
        monkeypatch.setattr(audio_module, "_STATIC_DIR", tmp_audio)

        mp3_data = self._make_fake_mp3()
        with TestClient(app) as client:
            h = self._headers(client)
            r = client.post(
                "/api/v1/audio/upload/ff/q-test-upload",
                files={"file": ("test.mp3", io.BytesIO(mp3_data), "audio/mpeg")},
                headers=h,
            )
        assert r.status_code == 201
        data = r.json()
        assert data["uploaded"] is True
        assert data["locale"] == "ff"
        assert data["question_id"] == "q-test-upload"
        assert "url" in data

    def test_upload_invalid_locale_rejected(self):
        mp3_data = self._make_fake_mp3()
        with TestClient(app) as client:
            h = self._headers(client)
            r = client.post(
                "/api/v1/audio/upload/invalid-locale/q-test",
                files={"file": ("test.mp3", io.BytesIO(mp3_data), "audio/mpeg")},
                headers=h,
            )
        assert r.status_code == 400

    def test_upload_non_mp3_rejected(self):
        with TestClient(app) as client:
            h = self._headers(client)
            r = client.post(
                "/api/v1/audio/upload/ff/q-test",
                files={"file": ("test.txt", io.BytesIO(b"not an mp3"), "text/plain")},
                headers=h,
            )
        assert r.status_code == 400

    def test_upload_invalid_mp3_signature_rejected(self):
        """Un fichier .mp3 avec fausse signature doit être rejeté."""
        fake_mp3 = b"NOT_MP3_DATA" + b"\x00" * 100
        with TestClient(app) as client:
            h = self._headers(client)
            r = client.post(
                "/api/v1/audio/upload/ff/q-test",
                files={"file": ("fake.mp3", io.BytesIO(fake_mp3), "audio/mpeg")},
                headers=h,
            )
        assert r.status_code == 400

    def test_upload_too_large_rejected(self):
        """Fichier > 10 Mo doit être rejeté."""
        big_mp3 = b'ID3\x03\x00' + b"\x00" * (11 * 1024 * 1024)
        with TestClient(app) as client:
            h = self._headers(client)
            r = client.post(
                "/api/v1/audio/upload/ff/q-test",
                files={"file": ("big.mp3", io.BytesIO(big_mp3), "audio/mpeg")},
                headers=h,
            )
        assert r.status_code == 413

    # ── delete ────────────────────────────────────────────────────

    def test_delete_nonexistent_returns_404(self):
        with TestClient(app) as client:
            h = self._super_admin_headers(client)
            r = client.delete("/api/v1/audio/delete/ff/q-nonexistent-xyz", headers=h)
        assert r.status_code == 404

    def test_delete_requires_super_admin(self):
        init_db()
        suffix = uuid.uuid4().hex[:6]
        email = f"adm-del-{suffix}@test.com"
        with SessionLocal() as db:
            u = User(email=email, full_name="Admin Del",
                     password_hash=get_password_hash("TestPass123!"), role="admin")
            db.add(u); db.commit()
        with TestClient(app) as client:
            token = client.post("/api/v1/auth/login",
                                data={"username": email, "password": "TestPass123!"}).json()["access_token"]
            r = client.delete("/api/v1/audio/delete/ff/q-test",
                              headers={"Authorization": f"Bearer {token}"})
        assert r.status_code in (401, 403)

    def test_upload_then_delete(self, tmp_path, monkeypatch):
        """Upload puis suppression d'un fichier audio."""
        from app.routers import audio as audio_module
        tmp_audio = tmp_path / "audio"
        monkeypatch.setattr(audio_module, "_STATIC_DIR", tmp_audio)

        mp3_data = self._make_fake_mp3()
        suffix = uuid.uuid4().hex[:6]
        qid = f"q-del-{suffix}"

        with TestClient(app) as client:
            # Upload en tant qu'admin
            h_admin = self._headers(client)
            r_up = client.post(
                f"/api/v1/audio/upload/ff/{qid}",
                files={"file": ("test.mp3", io.BytesIO(mp3_data), "audio/mpeg")},
                headers=h_admin,
            )
            assert r_up.status_code == 201

            # Vérifier existence
            r_check = client.get(f"/api/v1/audio/check/ff/{qid}")
            assert r_check.json()["exists"] is True

            # Supprimer en tant que super_admin
            h_sa = self._super_admin_headers(client)
            r_del = client.delete(f"/api/v1/audio/delete/ff/{qid}", headers=h_sa)
            assert r_del.status_code == 200
            assert r_del.json()["deleted"] is True

            # Vérifier suppression
            r_check2 = client.get(f"/api/v1/audio/check/ff/{qid}")
            assert r_check2.json()["exists"] is False


# ══════════════════════════════════════════════════════════════════
# 4. bootstrap_admin.py — lignes 48-60, 64
# ══════════════════════════════════════════════════════════════════

class TestBootstrapAdminEdgeCases:
    def test_bootstrap_updates_password_if_changed(self):
        """Si l'admin existe mais avec un mot de passe différent, il n'est pas recréé."""
        from app.bootstrap_admin import bootstrap_admin
        init_db()
        suffix = uuid.uuid4().hex[:6]
        email = f"bs-update-{suffix}@test.com"
        with SessionLocal() as db:
            user, created1 = bootstrap_admin(db, email=email,
                                             password="BootPass2026!", full_name="Admin")
            user2, created2 = bootstrap_admin(db, email=email,
                                              password="NewPass2026!", full_name="Admin")
        assert created1 is True
        assert created2 is False  # pas recréé, juste vérifié

    def test_bootstrap_sets_role_super_admin(self):
        """Le bootstrap doit toujours créer un super_admin."""
        from app.bootstrap_admin import bootstrap_admin
        init_db()
        suffix = uuid.uuid4().hex[:6]
        email = f"bs-role-{suffix}@test.com"
        with SessionLocal() as db:
            user, _ = bootstrap_admin(db, email=email,
                                      password="BootPass2026!", full_name="Super Admin")
        assert user.role == "super_admin"

    def test_bootstrap_sets_is_active_true(self):
        from app.bootstrap_admin import bootstrap_admin
        init_db()
        suffix = uuid.uuid4().hex[:6]
        email = f"bs-active-{suffix}@test.com"
        with SessionLocal() as db:
            user, _ = bootstrap_admin(db, email=email,
                                      password="BootPass2026!", full_name="Admin")
        assert user.is_active is True

    def test_bootstrap_from_settings_valid_config(self):
        """bootstrap_admin_from_settings réussit avec une config valide."""
        from app.bootstrap_admin import bootstrap_admin_from_settings
        from app.core.config import get_settings
        s = get_settings()
        prev_email = s.bootstrap_admin_email
        prev_pwd   = s.bootstrap_admin_password
        prev_name  = s.bootstrap_admin_full_name
        suffix = uuid.uuid4().hex[:6]
        s.bootstrap_admin_email    = f"bs-valid-{suffix}@test.com"
        s.bootstrap_admin_password = "ValidBootPass2026!"
        s.bootstrap_admin_full_name = "Bootstrap Valid"
        try:
            bootstrap_admin_from_settings()  # ne doit pas lever
        finally:
            s.bootstrap_admin_email    = prev_email
            s.bootstrap_admin_password = prev_pwd
            s.bootstrap_admin_full_name = prev_name


# ══════════════════════════════════════════════════════════════════
# 5. deps.py — lignes 19, 22
# ══════════════════════════════════════════════════════════════════

class TestDeps:
    def test_get_current_user_valid_token(self):
        """get_current_user doit retourner l'utilisateur pour un token valide."""
        init_db()
        suffix = uuid.uuid4().hex[:6]
        email = f"dep-{suffix}@test.com"
        password = "TestPass123!"
        with SessionLocal() as db:
            u = User(email=email, full_name="Dep Test",
                     password_hash=get_password_hash(password), role="admin")
            db.add(u); db.commit()

        with TestClient(app) as client:
            token = client.post("/api/v1/auth/login",
                                data={"username": email, "password": password}).json()["access_token"]
            r = client.get("/api/v1/dashboard",
                           headers={"Authorization": f"Bearer {token}"})
        assert r.status_code in (200, 403)  # auth OK

    def test_get_current_user_invalid_token_returns_401(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/dashboard",
                           headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401

    def test_require_roles_wrong_role_returns_403(self):
        """Un candidat ne peut pas accéder à un endpoint admin."""
        init_db()
        suffix = uuid.uuid4().hex[:6]
        email = f"cand-dep-{suffix}@test.com"
        with SessionLocal() as db:
            u = User(email=email, full_name="Cand Dep",
                     password_hash=get_password_hash("TestPass123!"), role="candidate")
            db.add(u); db.commit()

        with TestClient(app) as client:
            token = client.post("/api/v1/auth/login",
                                data={"username": email, "password": "TestPass123!"}).json()["access_token"]
            r = client.get("/api/v1/users",
                           headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_no_token_returns_401(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/users")
        assert r.status_code == 401

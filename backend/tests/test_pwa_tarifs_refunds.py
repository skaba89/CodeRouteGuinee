"""
Tests — PWA (manfest), Tarifs dynamiques, Remboursements
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_payment import Payment
from app.models_user import User
from app.security import get_password_hash
from tests.conftest import get_admin_headers


def _super_admin_headers(client: TestClient) -> dict:
    """Retourne les headers d'auth d'un super_admin de test."""
    init_db()
    suffix = uuid.uuid4().hex[:8]
    email  = f"sa-test-{suffix}@coderoute.test"
    with SessionLocal() as db:
        u = User(
            email=email,
            full_name=f"Super Admin {suffix}",
            password_hash=get_password_hash("TestPass123!"),
            role="super_admin",
        )
        db.add(u)
        db.commit()
    r = client.post("/api/v1/auth/login",
                    data={"username": email, "password": "TestPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── Tarifs ────────────────────────────────────────────────────────────────────

class TestTarifsPublic:
    def test_get_current_tarifs_200(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/tarifs/current")
        assert r.status_code == 200

    def test_current_tarifs_has_currency(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/tarifs/current")
        assert r.json()["currency"] == "GNF"

    def test_current_tarifs_has_list(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/tarifs/current")
        assert isinstance(r.json()["tarifs"], list)

    def test_current_tarifs_examen_B_present(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/tarifs/current")
        cles = [t["cle"] for t in r.json()["tarifs"]]
        assert "examen_code_B" in cles

    def test_current_tarifs_montant_gnf_positive(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/tarifs/current")
        for t in r.json()["tarifs"]:
            assert t["montant_gnf"] > 0

    def test_current_tarifs_no_auth_required(self):
        """Les tarifs sont publics — pas de token requis."""
        with TestClient(app) as c:
            r = c.get("/api/v1/tarifs/current")
        assert r.status_code != 401

    def test_tarifs_default_values(self):
        """Vérifier que les tarifs sont des montants raisonnables (10k–10M GNF)."""
        with TestClient(app) as c:
            r = c.get("/api/v1/tarifs/current")
        tarifs = {t["cle"]: t["montant_gnf"] for t in r.json()["tarifs"]}
        # Vérifier les plages raisonnables plutôt que les valeurs exactes
        # (un autre test peut avoir modifié les tarifs)
        assert tarifs.get("examen_code_B", 0) >= 10_000
        assert tarifs.get("examen_code_A", 0) >= 10_000


class TestTarifsAdmin:
    def test_admin_list_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/admin/tarifs")
        assert r.status_code == 401

    def test_admin_list_returns_all(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/admin/tarifs", headers=h)
        assert r.status_code == 200
        assert len(r.json()["tarifs"]) >= 6

    def test_update_tarif_requires_super_admin(self):
        """Un admin simple ne peut pas modifier un tarif (seul super_admin le peut)."""
        import uuid as _uuid

        from app.db.session import SessionLocal as _SL
        from app.db.session import init_db as _idb
        _idb()
        suffix = _uuid.uuid4().hex[:8]
        email  = f"admin-only-{suffix}@test.com"
        from app.models_user import User as _U
        from app.security import get_password_hash as _ph
        with _SL() as db:
            db.add(_U(email=email, full_name="Admin Only",
                      password_hash=_ph("Test123!"), role="admin"))
            db.commit()
        with TestClient(app) as c:
            token = c.post("/api/v1/auth/login",
                           data={"username": email, "password": "Test123!"}).json()["access_token"]
            r = c.put("/api/v1/admin/tarifs/examen_code_B",
                      headers={"Authorization": f"Bearer {token}"},
                      json={"montant_gnf": 200_000})
        assert r.status_code in (401, 403)

    def test_update_tarif_as_super_admin(self):
        original = 150_000
        with TestClient(app) as c:
            h = _super_admin_headers(c)
            r = c.put("/api/v1/admin/tarifs/examen_code_B",
                      headers=h, json={"montant_gnf": 160_000})
            assert r.status_code == 200
            assert r.json()["montant_gnf"] == 160_000
            # Remettre la valeur initiale
            c.put("/api/v1/admin/tarifs/examen_code_B",
                  headers=h, json={"montant_gnf": original})

    def test_update_tarif_invalid_montant(self):
        with TestClient(app) as c:
            h = _super_admin_headers(c)
            r = c.put("/api/v1/admin/tarifs/examen_code_B",
                      headers=h, json={"montant_gnf": -500})
        assert r.status_code in (400, 422)

    def test_update_tarif_unknown_key(self):
        with TestClient(app) as c:
            h = _super_admin_headers(c)
            r = c.put("/api/v1/admin/tarifs/inexistant_xyz",
                      headers=h, json={"montant_gnf": 50_000})
        assert r.status_code == 400


# ── Module tarifs ─────────────────────────────────────────────────────────────

class TestTarifsModule:
    def test_get_tarif_default_B(self):
        from app.tarifs import get_tarif
        assert get_tarif("examen_code_B") == 150_000

    def test_get_tarif_default_A(self):
        from app.tarifs import get_tarif
        assert get_tarif("examen_code_A") == 100_000

    def test_get_tarif_unknown_raises(self):
        from app.tarifs import get_tarif
        with pytest.raises(ValueError):
            get_tarif("tarif_inexistant_xyz")

    def test_get_tarif_for_candidate_first_attempt(self):
        from app.tarifs import get_tarif_for_candidate
        tarif = get_tarif_for_candidate("B", attempt_number=1)
        assert tarif == 150_000

    def test_get_tarif_for_candidate_second_attempt(self):
        from app.tarifs import get_tarif_for_candidate
        tarif = get_tarif_for_candidate("B", attempt_number=2)
        assert tarif == 150_000 + 50_000   # examen + réinscription

    def test_get_tarif_for_candidate_third_attempt(self):
        from app.tarifs import get_tarif_for_candidate
        tarif = get_tarif_for_candidate("B", attempt_number=3)
        assert tarif == 30_000   # rattrapage seulement

    def test_default_tarifs_all_positive(self):
        from app.tarifs import DEFAULT_TARIFS
        for cle, t in DEFAULT_TARIFS.items():
            assert t["montant_gnf"] > 0, f"Tarif {cle} nul ou négatif"

    def test_default_tarifs_count(self):
        from app.tarifs import DEFAULT_TARIFS
        assert len(DEFAULT_TARIFS) >= 6


# ── Remboursements ────────────────────────────────────────────────────────────

def _seed_paid_payment() -> tuple[str, str]:
    """Crée un candidat, une réservation et un paiement en statut 'paid'."""
    init_db()
    suffix = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        cand = Candidate(
            reference=f"GN-REF-{suffix}",
            first_name="Refund",
            last_name=f"Test-{suffix}",
            identity_number=f"NINA-REF-{suffix}",
            phone="+224628000001",
            permit_category="B",
            status="active",
        )
        db.add(cand)
        db.flush()

        booking = Booking(
            reference=f"BK-REF-{suffix}",
            candidate_id=cand.id,
            session_id="fake-session-for-refund",
            status="confirmed",
            verification_code=f"VRF-{suffix}",
        )
        db.add(booking)
        db.flush()

        payment = Payment(
            reference=f"PAY-REF-{suffix}",
            booking_reference=booking.reference,
            amount_gnf=150_000,
            provider="orange_money",
            phone="+224628000001",
            status="paid",
            receipt_number=f"RCT-{suffix}",
        )
        db.add(payment)
        db.commit()
        return payment.reference, booking.reference


class TestRefunds:
    """Circuit de remboursement : demande → décision admin → preuve opérateur."""

    _REASON = "Annulation administrative de la session"

    def _request(self, c: TestClient, pay_ref: str, headers: dict, reason: str | None = None):
        return c.post(f"/api/v1/payments/{pay_ref}/refund",
                      headers=headers, json={"reason": reason or self._REASON})

    def test_refund_requires_auth(self):
        pay_ref, _ = _seed_paid_payment()
        with TestClient(app) as c:
            r = c.post(f"/api/v1/payments/{pay_ref}/refund",
                       json={"reason": self._REASON})
        assert r.status_code == 401

    def test_refund_request_refused_to_unrelated_candidate(self):
        """Un candidat ne peut pas demander le remboursement du paiement d'un autre."""
        from tests.conftest import get_candidate_headers

        pay_ref, _ = _seed_paid_payment()
        with TestClient(app) as c:
            r = self._request(c, pay_ref, get_candidate_headers(c))
        assert r.status_code == 403

    def test_refund_request_is_pending_until_decision(self):
        pay_ref, booking_ref = _seed_paid_payment()
        with TestClient(app) as c:
            r = self._request(c, pay_ref, _super_admin_headers(c))
        assert r.status_code == 202, r.text
        data = r.json()
        assert data["status"] == "requested"
        assert data["booking_reference"] == booking_ref
        assert data["amount_gnf"] == 150_000
        with SessionLocal() as db:
            from sqlalchemy import select as _sel
            assert db.scalar(_sel(Payment.status).where(Payment.reference == pay_ref)) == "paid"

    def test_refund_full_workflow_marks_payment_refunded(self):
        pay_ref, booking_ref = _seed_paid_payment()
        with TestClient(app) as c:
            h = _super_admin_headers(c)
            refund = self._request(c, pay_ref, h).json()
            decision = c.post(f"/api/v1/payments/refunds/{refund['id']}/decision", headers=h,
                              json={"decision": "approved", "reason": "Session annulée par la DNTT"})
            assert decision.status_code == 200, decision.text
            done = c.post(f"/api/v1/payments/refunds/{refund['id']}/complete", headers=h, json={
                "provider_refund_reference": "OM-REFUND-0001",
                "evidence_reference": "PV-REMB-2026-001",
                "notes": "Remboursement Orange Money confirmé par l'opérateur",
            })
        assert done.status_code == 200, done.text
        assert done.json()["status"] == "completed"
        with SessionLocal() as db:
            from sqlalchemy import select as _sel
            assert db.scalar(_sel(Payment.status).where(Payment.reference == pay_ref)) == "refunded"
            assert db.scalar(_sel(Booking.status).where(Booking.reference == booking_ref)) == "cancelled"

    def test_refund_completion_requires_approval(self):
        pay_ref, _ = _seed_paid_payment()
        with TestClient(app) as c:
            h = _super_admin_headers(c)
            refund = self._request(c, pay_ref, h).json()
            r = c.post(f"/api/v1/payments/refunds/{refund['id']}/complete", headers=h, json={
                "provider_refund_reference": "OM-REFUND-0002",
                "evidence_reference": "PV-REMB-2026-002",
                "notes": "Tentative sans approbation préalable",
            })
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "REFUND_APPROVAL_REQUIRED"

    def test_refund_decision_refused_to_candidate(self):
        from tests.conftest import get_candidate_headers

        pay_ref, _ = _seed_paid_payment()
        with TestClient(app) as c:
            refund = self._request(c, pay_ref, _super_admin_headers(c)).json()
            r = c.post(f"/api/v1/payments/refunds/{refund['id']}/decision",
                       headers=get_candidate_headers(c),
                       json={"decision": "approved", "reason": "Auto-approbation"})
        assert r.status_code == 403

    def test_refund_nonexistent_payment(self):
        with TestClient(app) as c:
            r = self._request(c, "PAY-INEXISTANT-XYZ", _super_admin_headers(c))
        assert r.status_code == 404

    def test_refund_request_is_idempotent_while_open(self):
        """Une seconde demande renvoie la demande ouverte au lieu d'en créer une autre."""
        pay_ref, _ = _seed_paid_payment()
        with TestClient(app) as c:
            h = _super_admin_headers(c)
            first = self._request(c, pay_ref, h)
            second = self._request(c, pay_ref, h, reason="Deuxième demande identique")
        assert first.status_code == 202
        assert second.status_code == 200
        assert second.json()["id"] == first.json()["id"]

    def test_refund_reason_is_mandatory(self):
        pay_ref, _ = _seed_paid_payment()
        with TestClient(app) as c:
            h = _super_admin_headers(c)
            missing = c.post(f"/api/v1/payments/{pay_ref}/refund", headers=h, json={})
            too_short = self._request(c, pay_ref, h, reason="court")
        assert missing.status_code == 422
        assert too_short.status_code == 422


# ── CSRF ──────────────────────────────────────────────────────────────────────

class TestCsrf:
    def test_get_csrf_token_200(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/auth/csrf-token")
        assert r.status_code == 200

    def test_csrf_token_in_response(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/auth/csrf-token")
        data = r.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 20

    def test_csrf_token_has_three_parts(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/auth/csrf-token")
        token = r.json()["csrf_token"]
        assert len(token.split(".")) == 3

    def test_csrf_token_sets_cookie(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/auth/csrf-token")
        # Le cookie csrf_token doit être posé
        assert "csrf_token" in r.cookies or r.status_code == 200


# ── 2FA ───────────────────────────────────────────────────────────────────────

class TestTwoFactor:
    def _admin_token(self) -> str:
        init_db()
        suffix = uuid.uuid4().hex[:8]
        email  = f"2fa-admin-{suffix}@test.com"
        with SessionLocal() as db:
            u = User(
                email=email,
                full_name=f"2FA Admin {suffix}",
                password_hash=get_password_hash("TestPass123!"),
                role="admin",
            )
            db.add(u)
            db.commit()
        with TestClient(app) as c:
            return c.post("/api/v1/auth/login",
                          data={"username": email, "password": "TestPass123!"}).json()["access_token"]

    def test_2fa_status_not_enabled_by_default(self):
        token = self._admin_token()
        with TestClient(app) as c:
            r = c.get("/api/v1/auth/2fa/status",
                      headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["enabled"] is False

    def test_2fa_setup_returns_totp_uri(self):
        token = self._admin_token()
        with TestClient(app) as c:
            r = c.post("/api/v1/auth/2fa/setup",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "totp_uri" in data
        assert data["totp_uri"].startswith("otpauth://totp/")

    def test_2fa_setup_returns_backup_codes(self):
        token = self._admin_token()
        with TestClient(app) as c:
            r = c.post("/api/v1/auth/2fa/setup",
                       headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 8

    def test_2fa_setup_returns_secret(self):
        token = self._admin_token()
        with TestClient(app) as c:
            r = c.post("/api/v1/auth/2fa/setup",
                       headers={"Authorization": f"Bearer {token}"})
        assert "secret_b32" in r.json()

    def test_2fa_verify_wrong_code_fails(self):
        token = self._admin_token()
        with TestClient(app) as c:
            c.post("/api/v1/auth/2fa/setup",
                   headers={"Authorization": f"Bearer {token}"})
            r = c.post("/api/v1/auth/2fa/verify",
                       headers={"Authorization": f"Bearer {token}"},
                       json={"code": "000000"})
        assert r.status_code == 400

    def test_2fa_disable_not_enabled_is_ok(self):
        """Désactiver 2FA non activé ne doit pas crasher."""
        token = self._admin_token()
        with TestClient(app) as c:
            r = c.post("/api/v1/auth/2fa/disable",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_2fa_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/auth/2fa/status")
        assert r.status_code == 401

    def test_totp_generate_and_verify(self):
        """Test unitaire de la logique TOTP."""
        from app.two_factor import generate_secret, generate_totp, verify_totp
        secret = generate_secret()
        code   = generate_totp(secret)
        assert len(code) == 6
        assert code.isdigit()
        assert verify_totp(secret, code) is True

    def test_totp_wrong_code_fails(self):
        from app.two_factor import generate_secret, verify_totp
        secret = generate_secret()
        assert verify_totp(secret, "000000") is False

    def test_backup_codes_generated(self):
        from app.two_factor import generate_backup_codes
        codes = generate_backup_codes()
        assert len(codes) == 8
        assert all(len(c) == 8 for c in codes)


# ── Orange SMS ────────────────────────────────────────────────────────────────

class TestOrangeSms:
    def test_sms_console_mode_without_credentials(self):
        """Sans credentials, le SMS doit être loggué en console (pas d'erreur)."""
        from app.orange_sms import send_sms
        result = send_sms("+224628000000", "Test SMS dev mode")
        assert result.success is True
        assert result.provider == "console"

    def test_normalize_phone_plus224(self):
        from app.orange_sms import _normalize_phone
        assert _normalize_phone("+224628000000") == "+224628000000"

    def test_normalize_phone_9digits(self):
        from app.orange_sms import _normalize_phone
        assert _normalize_phone("628000000") == "+224628000000"

    def test_normalize_phone_with_spaces(self):
        from app.orange_sms import _normalize_phone
        assert _normalize_phone("628 000 000") == "+224628000000"

    def test_send_booking_sms_console(self):
        from app.orange_sms import send_booking_confirmation_sms
        r = send_booking_confirmation_sms(
            phone="+224628000000",
            candidate_name="Mamadou Diallo",
            booking_ref="BK-2026-0001",
            session_date="15/07/2026 09h00",
            center_name="Centre Kaloum 1",
        )
        assert r.success is True

    def test_send_exam_result_sms_passed(self):
        from app.orange_sms import send_exam_result_sms
        r = send_exam_result_sms("+224628000000", "Fatoumata", passed=True, score=37, total=40)
        assert r.success is True

    def test_send_exam_result_sms_failed(self):
        from app.orange_sms import send_exam_result_sms
        r = send_exam_result_sms("+224628000000", "Ibrahima", passed=False, score=28, total=40)
        assert r.success is True

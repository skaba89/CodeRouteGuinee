"""
Tests étendus Mobile Money — couverture Wave, PayDunya et chemins d'erreur.

Modules ciblés :
  app/mobile_money.py (42% → objectif 80%+)
"""
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest

from app.mobile_money import (
    ProviderResult,
    _sandbox_payment,
    _wave_payment,
    _paydunya_payment,
    normalize_provider,
    simulate_mobile_money_payment,
)


# ── normalize_provider ────────────────────────────────────────────

class TestNormalizeProvider:
    def test_orange_variants(self):
        assert normalize_provider("orange") == "orange_money"
        assert normalize_provider("Orange") == "orange_money"
        assert normalize_provider("orange_money") == "orange_money"
        assert normalize_provider("ORANGE MONEY") == "orange_money"

    def test_mtn_variants(self):
        assert normalize_provider("mtn") == "mtn_money"
        assert normalize_provider("MTN") == "mtn_money"
        assert normalize_provider("mtn_money") == "mtn_money"

    def test_wave_variants(self):
        assert normalize_provider("wave") == "wave"
        assert normalize_provider("Wave") == "wave"
        assert normalize_provider("wave_money") == "wave"

    def test_paydunya_variants(self):
        assert normalize_provider("paydunya") == "paydunya"
        assert normalize_provider("PayDunya") == "paydunya"
        assert normalize_provider("pay_dunya") == "paydunya"

    def test_sandbox_variants(self):
        assert normalize_provider("sandbox") == "sandbox"

    def test_unknown_fallback(self):
        assert normalize_provider("unknown") == "sandbox"
        assert normalize_provider("") == "sandbox"
        assert normalize_provider("  ") == "sandbox"


# ── _sandbox_payment ──────────────────────────────────────────────

class TestSandboxPayment:
    def test_always_succeeds(self):
        r = _sandbox_payment("orange_money", "+224620001234", 150_000)
        assert r.status == "paid"
        assert r.provider == "orange_money"
        assert "SANDBOX" in r.external_reference

    def test_short_phone_handled(self):
        r = _sandbox_payment("mtn_money", "12", 10_000)
        assert r.status == "paid"

    def test_reference_includes_phone_suffix(self):
        r = _sandbox_payment("wave", "+224620005678", 75_000)
        assert "5678" in r.external_reference


# ── _wave_payment ─────────────────────────────────────────────────

class TestWavePayment:
    def test_no_api_key_returns_failed(self):
        with patch.dict(os.environ, {"WAVE_API_KEY": ""}):
            r = _wave_payment("+224620001234", 150_000)
        assert r.status == "failed"
        assert "WAVE_API_KEY" in r.message.upper() or "key" in r.message.lower() or "Key" in r.message

    def test_success_201(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": "wave-checkout-abc123",
            "wave_launch_url": "https://wave.com/pay/abc123",
        }
        with patch.dict(os.environ, {"WAVE_API_KEY": "wave_sn_prod_test_key", "WAVE_BASE_URL": "https://api.wave.com"}):
            with patch("httpx.post", return_value=mock_resp):
                r = _wave_payment("+224620001234", 150_000)
        assert r.status == "pending"
        assert r.external_reference == "wave-checkout-abc123"
        assert r.provider == "wave"

    def test_success_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "wave-abc", "wave_launch_url": "https://wave.com/pay/abc"}
        with patch.dict(os.environ, {"WAVE_API_KEY": "test_key"}):
            with patch("httpx.post", return_value=mock_resp):
                r = _wave_payment("+224620001234", 75_000)
        assert r.status == "pending"

    def test_http_error_returns_failed(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        with patch.dict(os.environ, {"WAVE_API_KEY": "bad_key"}):
            with patch("httpx.post", return_value=mock_resp):
                r = _wave_payment("+224620001234", 150_000)
        assert r.status == "failed"
        assert "401" in r.external_reference

    def test_network_exception_returns_failed(self):
        import httpx
        with patch.dict(os.environ, {"WAVE_API_KEY": "test_key"}):
            with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
                r = _wave_payment("+224620001234", 150_000)
        assert r.status == "failed"
        assert "TIMEOUT" in r.external_reference.upper() or "timeout" in r.message.lower()


# ── _paydunya_payment ─────────────────────────────────────────────

class TestPaydunyaPayment:
    def test_missing_credentials_returns_failed(self):
        with patch.dict(os.environ, {
            "PAYDUNYA_MASTER_KEY": "",
            "PAYDUNYA_PRIVATE_KEY": "",
            "PAYDUNYA_TOKEN": "",
        }):
            r = _paydunya_payment("+224620001234", 150_000)
        assert r.status == "failed"
        assert "PAYDUNYA" in r.external_reference.upper() or "credential" in r.message.lower()

    def test_success_response_code_00(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response_code": "00",
            "token": "pd-token-abc123",
            "invoice_url": "https://paydunya.com/checkout/pd-token-abc123",
        }
        with patch.dict(os.environ, {
            "PAYDUNYA_MASTER_KEY": "mk_test",
            "PAYDUNYA_PRIVATE_KEY": "pk_test",
            "PAYDUNYA_TOKEN": "tk_test",
            "PAYDUNYA_MODE": "test",
        }):
            with patch("httpx.post", return_value=mock_resp):
                r = _paydunya_payment("+224620001234", 150_000)
        assert r.status == "pending"
        assert r.external_reference == "pd-token-abc123"

    def test_bad_response_code_returns_failed(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response_code": "99", "response_text": "Erreur"}
        mock_resp.text = '{"response_code":"99"}'
        with patch.dict(os.environ, {
            "PAYDUNYA_MASTER_KEY": "mk", "PAYDUNYA_PRIVATE_KEY": "pk", "PAYDUNYA_TOKEN": "tk",
        }):
            with patch("httpx.post", return_value=mock_resp):
                r = _paydunya_payment("+224620001234", 150_000)
        assert r.status == "failed"

    def test_http_500_returns_failed(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        with patch.dict(os.environ, {
            "PAYDUNYA_MASTER_KEY": "mk", "PAYDUNYA_PRIVATE_KEY": "pk", "PAYDUNYA_TOKEN": "tk",
        }):
            with patch("httpx.post", return_value=mock_resp):
                r = _paydunya_payment("+224620001234", 150_000)
        assert r.status == "failed"

    def test_network_exception_returns_failed(self):
        import httpx
        with patch.dict(os.environ, {
            "PAYDUNYA_MASTER_KEY": "mk", "PAYDUNYA_PRIVATE_KEY": "pk", "PAYDUNYA_TOKEN": "tk",
        }):
            with patch("httpx.post", side_effect=httpx.ConnectError("unreachable")):
                r = _paydunya_payment("+224620001234", 150_000)
        assert r.status == "failed"


# ── simulate_mobile_money_payment (dispatcher) ────────────────────

class TestSimulateMobileMoney:
    def test_sandbox_mode_always_sandbox(self):
        with patch.dict(os.environ, {"MOBILE_MONEY_MODE": "sandbox"}):
            r = simulate_mobile_money_payment("wave", "+224620001234", 50_000)
        assert r.status == "paid"
        assert "SANDBOX" in r.external_reference

    def test_production_wave_dispatched(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": "wave-prod-001", "wave_launch_url": "https://wave.com/x"}
        with patch.dict(os.environ, {
            "MOBILE_MONEY_MODE": "production",
            "WAVE_API_KEY": "wave_prod_key",
        }):
            with patch("httpx.post", return_value=mock_resp):
                r = simulate_mobile_money_payment("wave", "+224620001234", 150_000)
        assert r.provider == "wave"

    def test_production_paydunya_dispatched(self):
        with patch.dict(os.environ, {
            "MOBILE_MONEY_MODE": "production",
            "PAYDUNYA_MASTER_KEY": "", "PAYDUNYA_PRIVATE_KEY": "", "PAYDUNYA_TOKEN": "",
        }):
            r = simulate_mobile_money_payment("paydunya", "+224620001234", 150_000)
        assert r.provider == "paydunya"
        assert r.status == "failed"  # credentials manquants → échec attendu

    def test_production_unknown_falls_back_to_sandbox(self):
        with patch.dict(os.environ, {"MOBILE_MONEY_MODE": "production"}):
            r = simulate_mobile_money_payment("unknown_provider", "+224620001234", 50_000)
        assert r.status == "paid"  # sandbox forcé pour provider inconnu

    def test_production_exception_caught(self):
        with patch.dict(os.environ, {
            "MOBILE_MONEY_MODE": "production",
            "ORANGE_MONEY_CLIENT_ID": "id",
            "ORANGE_MONEY_CLIENT_SECRET": "secret",
        }):
            with patch("app.mobile_money._orange_money_payment",
                       side_effect=RuntimeError("API indisponible")):
                r = simulate_mobile_money_payment("orange", "+224620001234", 150_000)
        assert r.status == "failed"
        assert "API indisponible" in r.message or r.provider == "orange_money"

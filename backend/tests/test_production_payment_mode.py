"""Régression PAY-01 : aucun paiement simulé en environnement production."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import payment_provider_dispatcher as dispatcher
from app.core.config import Settings
from app.db.session import SessionLocal, init_db
from app.deps import get_current_user
from app.main import app
from app.mobile_money import ProviderResult
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_payment import Payment
from app.models_session import ExamSession
from app.models_user import User


def _production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "secret_key": "audit-test-jwt-value-only-1234567890-abcdef",
        "csrf_secret": "audit-test-csrf-different-value-0987654321",
        "database_url": "postgresql+psycopg://unused:unused@db.invalid/test",
        "cors_origins": "https://app.invalid",
        "allowed_hosts": "app.invalid",
        "enable_api_docs": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("environment", ["production", "Production", " PRODUCTION "])
@pytest.mark.parametrize("mode", ["sandbox", "", "invalid"])
def test_startup_rejects_simulation_in_production(environment, mode) -> None:
    with pytest.raises(RuntimeError, match="MOBILE_MONEY_MODE"):
        _production_settings(environment=environment, mobile_money_mode=mode).validate_production_secrets()


def test_startup_rejects_default_sandbox(monkeypatch) -> None:
    monkeypatch.delenv("MOBILE_MONEY_MODE", raising=False)
    with pytest.raises(RuntimeError, match="MOBILE_MONEY_MODE"):
        _production_settings().validate_production_secrets()


@pytest.mark.parametrize("mode", ["production", " Production "])
def test_startup_accepts_explicit_real_payment_mode(mode) -> None:
    _production_settings(mobile_money_mode=mode).validate_production_secrets()


@pytest.mark.parametrize("environment", ["development", "test", "staging"])
def test_non_production_startup_preserves_simulation(environment) -> None:
    Settings(_env_file=None, environment=environment, mobile_money_mode="sandbox").validate_production_secrets()


@pytest.fixture
def no_provider_calls(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        pytest.fail("Le garde de production doit bloquer avant tout provider/sandbox")

    for name in (
        "_sandbox_payment", "_celcom_money_payment_safe", "_orange_money_payment",
        "_mtn_money_payment", "_wave_payment", "_paydunya_payment",
    ):
        monkeypatch.setattr(dispatcher, name, forbidden)
    return calls


@pytest.mark.parametrize("environment", ["production", "Production", " PRODUCTION "])
@pytest.mark.parametrize("mode", [None, "", "sandbox", "prodution"])
@pytest.mark.parametrize("provider", ["wave", "orange_money", "mtn_money", "paydunya", "celcom_money", "sandbox"])
def test_dispatcher_refuses_all_simulation_paths(monkeypatch, no_provider_calls, environment, mode, provider) -> None:
    # Le cache peut avoir été construit en test : l'override effectif prime.
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setattr(dispatcher, "get_settings", lambda: SimpleNamespace(environment="test", mobile_money_mode="sandbox"))
    if mode is None:
        monkeypatch.delenv("MOBILE_MONEY_MODE", raising=False)
    else:
        monkeypatch.setenv("MOBILE_MONEY_MODE", mode)
    result = dispatcher.dispatch_mobile_money_payment(provider, "+224600000000", 150_000)
    assert result.status == "failed"
    assert "MOBILE_MONEY_MODE" in result.message
    assert not no_provider_calls


def test_dispatcher_also_checks_settings_when_environment_variables_absent(monkeypatch, no_provider_calls) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("MOBILE_MONEY_MODE", raising=False)
    monkeypatch.setattr(dispatcher, "get_settings", lambda: SimpleNamespace(environment="production", mobile_money_mode="sandbox"))
    assert dispatcher.dispatch_mobile_money_payment("wave", "+224600000000", 150_000).status == "failed"
    assert not no_provider_calls


@pytest.mark.parametrize("provider", ["wave", "orange_money", "mtn_money", "paydunya"])
def test_production_dispatch_keeps_real_provider_contract(monkeypatch, provider) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MOBILE_MONEY_MODE", " Production ")
    monkeypatch.setenv("PAYDUNYA_MODE", "live")
    monkeypatch.setenv("MTN_MONEY_ENVIRONMENT", "contracted-live-target")
    monkeypatch.setenv("MTN_MONEY_BASE_URL", "https://live.mtn.invalid")
    calls = []
    expected = ProviderResult(provider=provider, status="pending", external_reference="TEST-ONLY", message="stub")

    def fake_real_provider(phone, amount):
        calls.append((phone, amount))
        return expected

    monkeypatch.setattr(dispatcher, f"_{provider}_payment", fake_real_provider)
    assert dispatcher.dispatch_mobile_money_payment(provider, "+224600000000", 150_000) is expected
    assert calls == [("+224600000000", 150_000)]


@pytest.mark.parametrize("mode", [None, "test", "sandbox", "LIVE"])
def test_production_refuses_paydunya_test_mode(monkeypatch, no_provider_calls, mode) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MOBILE_MONEY_MODE", "production")
    if mode is None:
        monkeypatch.delenv("PAYDUNYA_MODE", raising=False)
    else:
        monkeypatch.setenv("PAYDUNYA_MODE", mode)
    result = dispatcher.dispatch_mobile_money_payment("paydunya", "+224600000000", 150_000)
    assert result.status == "failed"
    assert "PAYDUNYA_MODE" in result.message
    assert not no_provider_calls


@pytest.mark.parametrize("target,url", [
    (None, None),
    ("sandbox", "https://live.mtn.invalid"),
    ("test", "https://live.mtn.invalid"),
    ("contracted-live-target", None),
    ("contracted-live-target", "https://sandbox.momodeveloper.mtn.com"),
    ("contracted-live-target", "http://live.mtn.invalid"),
    ("contracted-live-target", "https://"),
    ("contracted-live-target", "https://["),
])
def test_production_refuses_mtn_sandbox_configuration(monkeypatch, no_provider_calls, target, url) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MOBILE_MONEY_MODE", "production")
    for key, value in (("MTN_MONEY_ENVIRONMENT", target), ("MTN_MONEY_BASE_URL", url)):
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    result = dispatcher.dispatch_mobile_money_payment("mtn_money", "+224600000000", 150_000)
    assert result.status == "failed"
    assert "MTN_MONEY_" in result.message
    assert not no_provider_calls


@pytest.mark.parametrize("environment", ["development", "test", "staging"])
def test_non_production_sandbox_still_works(monkeypatch, environment) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("MOBILE_MONEY_MODE", "sandbox")
    result = dispatcher.dispatch_mobile_money_payment("wave", "+224600000000", 150_000)
    assert result.status == "paid"
    assert result.external_reference.startswith("SANDBOX-")


def test_http_payment_cannot_settle_booking_when_runtime_configuration_is_unsafe(monkeypatch, no_provider_calls) -> None:
    """Défense runtime même si le contrôle de démarrage a été contourné."""
    init_db()
    marker = uuid4().hex
    with SessionLocal() as db:
        user = User(email=f"{marker}@test.invalid", full_name="Test", password_hash="unused", role="candidate", is_active=True)
        db.add(user)
        db.flush()
        candidate = Candidate(reference=f"PAY-TEST-{marker}", first_name="Test", last_name="Test",
                              identity_number=marker, phone="+224600000000", permit_category="B",
                              status="verified", user_id=user.id)
        center = Center(code=marker, name="Test", city="Conakry", address="Test", capacity=35, status="accredited")
        db.add_all([candidate, center])
        db.flush()
        session = ExamSession(reference=marker, center_id=center.id,
                              starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1), capacity=35, status="open")
        db.add(session)
        db.flush()
        booking = Booking(reference=marker, candidate_id=candidate.id, session_id=session.id,
                          status="confirmed", verification_code=marker)
        db.add(booking)
        db.commit()
        db.refresh(user)
        app.dependency_overrides[get_current_user] = lambda: user
        try:
            with TestClient(app) as client:
                monkeypatch.setenv("ENVIRONMENT", "production")
                monkeypatch.setenv("MOBILE_MONEY_MODE", "sandbox")
                response = client.post("/api/v1/payments", json={
                    "booking_reference": marker, "provider": "wave", "phone": "+224600000000",
                })
            assert response.status_code == 201
            assert response.json()["status"] == "failed"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
    with SessionLocal() as db:
        persisted_booking = db.scalar(select(Booking).where(Booking.reference == marker))
        payments = db.scalars(select(Payment).where(Payment.booking_reference == marker)).all()
        assert persisted_booking.status == "confirmed"
        assert persisted_booking.payment_reference is None
        assert len(payments) == 1 and payments[0].status == "failed"
        assert payments[0].paid_at is None
    assert not no_provider_calls

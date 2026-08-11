from __future__ import annotations

from types import SimpleNamespace

from app import payment_provider_dispatcher as dispatcher
from app.mobile_money import ProviderResult
from app.payment_provider_dispatcher import dispatch_mobile_money_payment
from app.routers import payments


def test_payments_router_uses_fail_closed_dispatcher() -> None:
    assert payments.simulate_mobile_money_payment is dispatch_mobile_money_payment


def test_unknown_provider_never_becomes_paid_sandbox(monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_MONEY_MODE", "sandbox")
    result = dispatch_mobile_money_payment("unknown_wallet", "+224622000099", 150_000)
    assert result.status == "failed"
    assert result.provider == "unknown_wallet"
    assert result.external_reference.startswith("ERR-")


def test_empty_provider_never_becomes_paid_sandbox(monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_MONEY_MODE", "sandbox")
    result = dispatch_mobile_money_payment("", "+224622000099", 150_000)
    assert result.status == "failed"
    assert result.provider == "unknown"
    assert result.external_reference.startswith("ERR-")


def test_sandbox_provider_is_refused_in_production(monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_MONEY_MODE", "production")
    result = dispatch_mobile_money_payment("sandbox", "+224622000099", 150_000)
    assert result.status == "failed"
    assert result.provider == "sandbox"
    assert "désactivé en production" in result.message


def test_celcom_success_builds_valid_provider_result(monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_MONEY_MODE", "sandbox")
    monkeypatch.setenv("CELCOM_MONEY_CLIENT_ID", "client-id")
    monkeypatch.setenv("CELCOM_MONEY_CLIENT_SECRET", "client-secret")

    responses = iter([
        SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"access_token": "token"}),
        SimpleNamespace(raise_for_status=lambda: None, json=lambda: {}),
    ])
    import httpx
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: next(responses))

    result = dispatch_mobile_money_payment("celcom_money", "+224622000099", 150_000)
    assert result.provider == "celcom_money"
    assert result.status == "pending"
    assert result.external_reference
    assert "Celcom" in result.message


def test_celcom_network_failure_returns_failed_result_with_reference(monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_MONEY_MODE", "sandbox")
    monkeypatch.setenv("CELCOM_MONEY_CLIENT_ID", "client-id")
    monkeypatch.setenv("CELCOM_MONEY_CLIENT_SECRET", "client-secret")

    import httpx

    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(httpx, "post", boom)
    result = dispatch_mobile_money_payment("celcom_money", "+224622000099", 150_000)
    assert result.provider == "celcom_money"
    assert result.status == "failed"
    assert result.external_reference.startswith("ERR-CELCOM-")
    assert "network down" in result.message


def test_paydunya_legacy_message_is_normalized_to_https_checkout_url(monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_MONEY_MODE", "production")

    monkeypatch.setattr(
        dispatcher,
        "_paydunya_payment",
        lambda phone, amount: ProviderResult(
            provider="paydunya",
            status="pending",
            external_reference="PD-TOKEN-123",
            message="Paiement PayDunya initié — URL: https://paydunya.test/invoice/PD-TOKEN-123",
        ),
    )
    result = dispatcher.dispatch_mobile_money_payment(
        "paydunya", "+224622000099", 150_000
    )
    assert result.status == "pending"
    assert result.checkout_url == "https://paydunya.test/invoice/PD-TOKEN-123"
    assert "URL:" not in result.message


def test_paydunya_non_https_message_is_never_promoted_to_checkout_url(monkeypatch) -> None:
    monkeypatch.setenv("MOBILE_MONEY_MODE", "production")
    monkeypatch.setattr(
        dispatcher,
        "_paydunya_payment",
        lambda phone, amount: ProviderResult(
            provider="paydunya",
            status="pending",
            external_reference="PD-TOKEN-HTTP",
            message="Paiement PayDunya initié — URL: http://unsafe.example/invoice/PD-TOKEN-HTTP",
        ),
    )
    result = dispatcher.dispatch_mobile_money_payment(
        "paydunya", "+224622000099", 150_000
    )
    assert result.status == "pending"
    assert result.checkout_url == ""

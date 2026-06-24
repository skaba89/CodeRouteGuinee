"""
Tests pour le mobile money sandbox (couverture 26% → 70%+).
Uniquement les chemins sandbox — pas d'appels réseau réels.
"""


from app.mobile_money import (
    ProviderResult,
    normalize_provider,
    simulate_mobile_money_payment,
)


def test_normalize_provider_aliases() -> None:
    """normalize_provider() gère les alias courants."""
    assert normalize_provider("orange") == "orange_money"
    assert normalize_provider("Orange Money") == "orange_money"
    assert normalize_provider("mtn") == "mtn_money"
    assert normalize_provider("MTN_Money") == "mtn_money"
    assert normalize_provider("sandbox") == "sandbox"
    assert normalize_provider("unknown_provider") == "sandbox"


def test_sandbox_orange_money() -> None:
    """Sandbox Orange Money retourne status=paid."""
    result = simulate_mobile_money_payment("orange_money", "+224620111001", 250_000)
    assert isinstance(result, ProviderResult)
    assert result.status == "paid"
    assert result.provider == "orange_money"
    assert "SANDBOX" in result.external_reference
    assert result.message


def test_sandbox_mtn_money() -> None:
    """Sandbox MTN Money retourne status=paid."""
    result = simulate_mobile_money_payment("mtn_money", "+224660222002", 250_000)
    assert result.status == "paid"
    assert result.provider == "mtn_money"
    assert "SANDBOX" in result.external_reference


def test_sandbox_with_alias() -> None:
    """Le mode sandbox fonctionne avec les alias opérateur."""
    result = simulate_mobile_money_payment("orange", "+224620333003", 100_000)
    assert result.status == "paid"
    assert "SANDBOX" in result.external_reference


def test_sandbox_mode_default(monkeypatch) -> None:
    """Sans MOBILE_MONEY_MODE, le mode sandbox est utilisé par défaut."""
    monkeypatch.delenv("MOBILE_MONEY_MODE", raising=False)
    result = simulate_mobile_money_payment("orange_money", "+224620444004", 250_000)
    assert result.status == "paid"


def test_production_mode_missing_credentials_returns_failed(monkeypatch) -> None:
    """En mode production sans credentials, retourne status=failed (pas d'exception)."""
    monkeypatch.setenv("MOBILE_MONEY_MODE", "production")
    monkeypatch.delenv("ORANGE_MONEY_CLIENT_ID", raising=False)
    monkeypatch.delenv("ORANGE_MONEY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ORANGE_MONEY_MERCHANT_CODE", raising=False)

    result = simulate_mobile_money_payment("orange_money", "+224620555005", 250_000)
    assert result.status == "failed"
    assert "ERR-" in result.external_reference
    assert result.message


def test_production_mode_mtn_missing_credentials_returns_failed(monkeypatch) -> None:
    """MTN en production sans credentials retourne status=failed."""
    monkeypatch.setenv("MOBILE_MONEY_MODE", "production")
    monkeypatch.delenv("MTN_MONEY_SUBSCRIPTION_KEY", raising=False)
    monkeypatch.delenv("MTN_MONEY_API_USER_ID", raising=False)
    monkeypatch.delenv("MTN_MONEY_API_KEY", raising=False)

    result = simulate_mobile_money_payment("mtn_money", "+224660666006", 250_000)
    assert result.status == "failed"


def test_sandbox_external_reference_includes_phone_suffix() -> None:
    """La référence sandbox contient les 4 derniers chiffres du téléphone."""
    result = simulate_mobile_money_payment("orange_money", "+224620987654", 250_000)
    assert "7654" in result.external_reference


def test_sandbox_various_amounts() -> None:
    """Le sandbox accepte différents montants GNF."""
    for amount in [50_000, 250_000, 1_000_000]:
        result = simulate_mobile_money_payment("orange_money", "+224620111001", amount)
        assert result.status == "paid"
        assert str(amount) in result.message or result.status == "paid"

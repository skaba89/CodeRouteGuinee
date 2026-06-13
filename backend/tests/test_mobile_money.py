from app.mobile_money import normalize_provider, simulate_mobile_money_payment


def test_provider_aliases_are_normalized() -> None:
    assert normalize_provider("Orange") == "orange_money"
    assert normalize_provider("MTN") == "mtn_money"
    assert normalize_provider("unknown") == "sandbox"


def test_mobile_money_sandbox_returns_paid_result() -> None:
    result = simulate_mobile_money_payment("orange", "+224611111111", 250000)
    assert result.provider == "orange_money"
    assert result.status == "paid"
    assert result.external_reference.startswith("ORANGE_MONEY-")

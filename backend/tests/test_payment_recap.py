from types import SimpleNamespace

from app.payment_recap import summarize_payments


def test_payment_recap_groups_by_status_and_provider() -> None:
    payments = [
        SimpleNamespace(amount_gnf=250000, status="paid", provider="orange_money"),
        SimpleNamespace(amount_gnf=250000, status="paid", provider="mtn_money"),
        SimpleNamespace(amount_gnf=100000, status="failed", provider="orange_money"),
    ]
    recap = summarize_payments(payments)
    assert recap["total_count"] == 3
    assert recap["total_amount_gnf"] == 600000
    assert recap["by_status"]["paid"]["count"] == 2
    assert recap["by_provider"]["orange_money"]["amount_gnf"] == 350000

from collections import defaultdict
from typing import Iterable


def summarize_payments(payments: Iterable[object]) -> dict:
    total_amount = 0
    total_count = 0
    by_status: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount_gnf": 0})
    by_provider: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount_gnf": 0})

    for payment in payments:
        amount = int(payment.amount_gnf or 0)
        total_count += 1
        total_amount += amount
        by_status[payment.status]["count"] += 1
        by_status[payment.status]["amount_gnf"] += amount
        by_provider[payment.provider]["count"] += 1
        by_provider[payment.provider]["amount_gnf"] += amount

    return {
        "total_count": total_count,
        "total_amount_gnf": total_amount,
        "by_status": dict(by_status),
        "by_provider": dict(by_provider),
    }

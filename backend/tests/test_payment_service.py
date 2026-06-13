from app.payment_service import build_payment_reference, build_receipt_number


def test_payment_reference_and_receipt_number() -> None:
    reference = build_payment_reference(1)
    receipt = build_receipt_number(reference)
    assert reference.startswith("GN-PAY-")
    assert receipt.startswith("GN-RECEIPT-")

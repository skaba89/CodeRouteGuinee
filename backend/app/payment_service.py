from datetime import UTC, datetime


def build_payment_reference(sequence_number: int) -> str:
    return f"GN-PAY-{datetime.now(UTC).replace(tzinfo=None).year}-{sequence_number:06d}"


def build_receipt_number(reference: str) -> str:
    return reference.replace("GN-PAY", "GN-RECEIPT")

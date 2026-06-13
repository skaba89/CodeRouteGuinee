from datetime import datetime


def build_payment_reference(sequence_number: int) -> str:
    return f"GN-PAY-{datetime.utcnow().year}-{sequence_number:06d}"


def build_receipt_number(reference: str) -> str:
    return reference.replace("GN-PAY", "GN-RECEIPT")

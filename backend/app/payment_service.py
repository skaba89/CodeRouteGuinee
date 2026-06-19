from app.time_utils import utc_now


def build_payment_reference(sequence_number: int) -> str:
    return f"GN-PAY-{utc_now().year}-{sequence_number:06d}"


def build_receipt_number(reference: str) -> str:
    return reference.replace("GN-PAY", "GN-RECEIPT")

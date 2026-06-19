import hashlib
import secrets
from app.time_utils import utc_now


def build_booking_reference(sequence_number: int) -> str:
    return f"GN-CONV-{utc_now().year}-{sequence_number:06d}"


def build_verification_code(reference: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.sha256(f"{reference}:{salt}".encode()).hexdigest()[:24].upper()
    return f"{reference}-{digest}"

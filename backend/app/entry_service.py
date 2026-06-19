from app.time_utils import utc_now


def build_entry_success(reference: str, center_code: str | None = None) -> dict:
    return {
        "allowed": True,
        "reference": reference,
        "status": "checked_in",
        "center_code": center_code,
        "checked_in_at": utc_now().isoformat(),
        "message": "Candidate entry validated",
    }


def build_entry_denied(reference: str, reason: str) -> dict:
    return {
        "allowed": False,
        "reference": reference,
        "status": "denied",
        "reason": reason,
        "checked_in_at": utc_now().isoformat(),
    }

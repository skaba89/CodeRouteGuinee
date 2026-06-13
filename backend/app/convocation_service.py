from datetime import datetime


def build_qr_payload(reference: str, verification_code: str) -> str:
    return f"CODEROUTE-GN|REF={reference}|VERIFY={verification_code}"


def build_convocation_payload(booking: object, candidate: object, session: object, center: object) -> dict:
    return {
        "title": "Convocation examen CodeRoute Guinee",
        "reference": booking.reference,
        "candidate": {
            "id": candidate.id,
            "full_name": f"{candidate.first_name} {candidate.last_name}",
            "identity_number": candidate.identity_number,
            "phone": candidate.phone,
            "permit_category": candidate.permit_category,
        },
        "session": {
            "id": session.id,
            "reference": session.reference,
            "starts_at": session.starts_at.isoformat(),
        },
        "center": {
            "id": center.id,
            "name": center.name,
            "city": center.city,
            "address": center.address,
        },
        "verification_code": booking.verification_code,
        "qr_payload": build_qr_payload(booking.reference, booking.verification_code),
        "issued_at": datetime.utcnow().isoformat(),
    }

"""L'attestation de résultat porte un QR de vérification publique."""
from __future__ import annotations

from app.pdf_service import build_result_certificate_pdf

_ARGS = dict(
    candidate={"reference": "GN-CAND-QR", "full_name": "Mamadou Diallo",
               "identity_number": "GN-NINA-QR", "permit_category": "B"},
    session={"reference": "GN-SESSION-QR", "starts_at": "2026-10-10T09:00:00"},
    center={"name": "Centre Kaloum 1", "city": "Conakry"},
    attempt={"score": 38, "passed": True, "status": "submitted", "submitted_at": "2026-10-10T09:30:00"},
)


def test_certificate_embeds_verification_qr_only_when_url_given() -> None:
    with_qr = build_result_certificate_pdf(**_ARGS, verification_url="https://coderoute.gov.gn/#/verifier/ATT-1")
    without_qr = build_result_certificate_pdf(**_ARGS)

    assert with_qr.startswith(b"%PDF")
    assert b"/Subtype /Image" in with_qr
    assert b"/Subtype /Image" not in without_qr

from app.pdf_service import build_convocation_pdf, build_simple_pdf


def test_build_simple_pdf_returns_pdf_bytes() -> None:
    content = build_simple_pdf("CodeRoute Guinee", ["Reference: GN-CONV-2026-000001", "Status: confirmed"])
    assert content.startswith(b"%PDF")
    assert b"xref" in content
    assert b"%%EOF" in content


def test_build_convocation_pdf_contains_official_sections() -> None:
    content = build_convocation_pdf(
        {
            "reference": "GN-BOOK-2026-000001",
            "issued_at": "2026-06-17T12:00:00",
            "verification_code": "123456",
            "qr_payload": "CODEROUTE-GN|REF=GN-BOOK-2026-000001|VERIFY=123456",
            "candidate": {
                "reference": "GN-CODE-2026-000001",
                "full_name": "Aminata Diallo",
                "identity_number": "NINA-001",
                "phone": "+224622000000",
                "permit_category": "B",
            },
            "session": {"reference": "GN-SESSION-2026-001", "starts_at": "2026-06-20T09:00:00"},
            "center": {"code": "CTR-KALOUM", "name": "Centre Kaloum", "city": "Conakry", "address": "Kaloum"},
        }
    )

    # PDF valide et non trivial
    assert content.startswith(b"%PDF")
    assert content.rstrip().endswith(b"%%EOF")
    assert len(content) > 3000  # QR + mise en page

    # Contenu texte vérifié via extraction (accents corrects, sections)
    from pypdf import PdfReader
    from io import BytesIO
    text = PdfReader(BytesIO(content)).pages[0].extract_text()
    assert "CONVOCATION" in text.upper()
    assert "Aminata Diallo" in text
    assert "GN-CODE-2026-000001" in text
    assert "CONTRÔLE D'ENTRÉE" in text.upper()
    assert "CONSIGNES" in text.upper()
    assert "123456" in text  # code de vérification
    assert "RÉPUBLIQUE DE GUINÉE" in text  # accents préservés

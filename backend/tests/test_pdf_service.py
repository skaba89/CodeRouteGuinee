from app.pdf_service import build_simple_pdf


def test_build_simple_pdf_returns_pdf_bytes() -> None:
    content = build_simple_pdf("CodeRoute Guinee", ["Reference: GN-CONV-2026-000001", "Status: confirmed"])
    assert content.startswith(b"%PDF")
    assert b"xref" in content
    assert b"%%EOF" in content

from app.entry_service import build_entry_denied, build_entry_success


def test_entry_success_payload() -> None:
    result = build_entry_success("GN-CONV-2026-000001", "CTR-001")
    assert result["allowed"] is True
    assert result["status"] == "checked_in"


def test_entry_denied_payload() -> None:
    result = build_entry_denied("GN-CONV-2026-000001", "bad_code")
    assert result["allowed"] is False
    assert result["status"] == "denied"

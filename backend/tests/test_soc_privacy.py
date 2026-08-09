import logging

import pytest

from app import soc_privacy
from app.soc_config import get_soc_settings


@pytest.fixture(autouse=True)
def _clear_soc_cache_after_test():
    yield
    get_soc_settings.cache_clear()


def _enable_soc(monkeypatch) -> None:
    monkeypatch.setenv("SOC_PSEUDONYM_KEY", "soc-privacy-test-key-" + ("x" * 40))
    get_soc_settings.cache_clear()


def test_pseudonym_is_deterministic_and_namespace_separated(monkeypatch) -> None:
    _enable_soc(monkeypatch)
    value = "98f3be30-a5bf-4a2d-a093-e4a8b7651e4a"
    first = soc_privacy.pseudonymize(value, "usr")
    assert first == soc_privacy.pseudonymize(value, "usr")
    assert first != soc_privacy.pseudonymize(value, "cand")
    assert value not in first


def test_context_removes_raw_email_ip_uuid_and_secrets(monkeypatch) -> None:
    _enable_soc(monkeypatch)
    user_id = "98f3be30-a5bf-4a2d-a093-e4a8b7651e4a"
    context = {
        "user_id": user_id,
        "email": "citoyen@example.gn",
        "ip": "196.200.1.24",
        "authorization": "Bearer secret-token-value",
        "url": "https://api.example.gn/exams/123?email=citoyen@example.gn",
        "nested": {"candidate_id": user_id, "note": f"actor {user_id} from 196.200.1.24"},
    }
    safe = soc_privacy.sanitize_context(context)
    text = str(safe)
    for raw in (user_id, "citoyen@example.gn", "196.200.1.24", "secret-token-value", "https://api.example.gn"):
        assert raw not in text
    assert safe["authorization"] == "***REDACTED***"
    assert safe["url"] == "***REDACTED***"
    assert str(safe["user_id"]).startswith("usr:")
    assert str(safe["email"]).startswith("email:")
    assert str(safe["ip"]).startswith("ip:")


def test_free_text_pseudonymizes_raw_identifiers(monkeypatch) -> None:
    _enable_soc(monkeypatch)
    uuid = "98f3be30-a5bf-4a2d-a093-e4a8b7651e4a"
    safe = soc_privacy.sanitize_free_text(f"user {uuid} citoyen@example.gn from 196.200.1.24")
    assert uuid not in safe
    assert "citoyen@example.gn" not in safe
    assert "196.200.1.24" not in safe
    assert "uuid:" in safe
    assert "email:" in safe
    assert "ip:" in safe


def test_log_filter_never_emits_raw_structured_identifiers(monkeypatch) -> None:
    _enable_soc(monkeypatch)
    uuid = "98f3be30-a5bf-4a2d-a093-e4a8b7651e4a"
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=f"candidate {uuid} from 196.200.1.24",
        args=(),
        exc_info=None,
    )
    record.candidate_id = uuid
    record.ip = "196.200.1.24"
    record.email = "citoyen@example.gn"
    assert soc_privacy.SOCPrivacyFilter().filter(record) is True
    text = f"{record.msg} {record.candidate_id} {record.ip} {record.email}"
    assert uuid not in text
    assert "196.200.1.24" not in text
    assert "citoyen@example.gn" not in text

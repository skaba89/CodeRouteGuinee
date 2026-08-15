from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

import pytest

from scripts import verify_render_deployment as verifier


EXPECTED = "0123456789abcdef0123456789abcdef01234567"


def _live(commit=EXPECTED, repo="skaba89/CodeRouteGuinee"):
    return {
        "status": "ok",
        "runtime": {
            "git_commit": commit,
            "git_branch": "main",
            "git_repo_slug": repo,
            "render_service_name": "coderoute-backend",
            "render_instance_id": "srv-instance-1",
        },
    }


def test_deployed_sha_receipt_passes_only_for_matching_ready_runtime() -> None:
    result = verifier.evaluate_runtime(
        _live(),
        {"status": "ready"},
        expected_commit=EXPECTED,
        expected_repo_slug="skaba89/CodeRouteGuinee",
    )
    assert result["passed"] is True
    assert result["blockers"] == []
    assert result["deployed_commit"] == EXPECTED
    assert result["git_branch"] == "main"


def test_deployed_sha_mismatch_is_blocking() -> None:
    result = verifier.evaluate_runtime(
        _live("f" * 40),
        {"status": "ready"},
        expected_commit=EXPECTED,
        expected_repo_slug="skaba89/CodeRouteGuinee",
    )
    assert result["passed"] is False
    assert "DEPLOYED_SHA_MATCH" in result["blockers"]


def test_missing_render_commit_is_blocking_even_when_health_is_green() -> None:
    result = verifier.evaluate_runtime(
        _live(""),
        {"status": "ready"},
        expected_commit=EXPECTED,
    )
    assert result["passed"] is False
    assert "RENDER_GIT_COMMIT_PRESENT" in result["blockers"]
    assert "DEPLOYED_SHA_MATCH" in result["blockers"]


def test_readiness_failure_is_blocking() -> None:
    result = verifier.evaluate_runtime(
        _live(),
        {"status": "not_ready"},
        expected_commit=EXPECTED,
    )
    assert result["passed"] is False
    assert "READINESS_OK" in result["blockers"]


def test_expected_commit_requires_full_sha() -> None:
    with pytest.raises(ValueError):
        verifier.evaluate_runtime(_live(), {"status": "ready"}, expected_commit="deadbee")


def test_safe_base_url_rejects_remote_plain_http_and_credentials() -> None:
    assert verifier.safe_base_url("https://coderouteguinee-backend.onrender.com/") == "https://coderouteguinee-backend.onrender.com"
    assert verifier.safe_base_url("http://localhost:8000") == "http://localhost:8000"
    with pytest.raises(ValueError):
        verifier.safe_base_url("http://example.org")
    with pytest.raises(ValueError):
        verifier.safe_base_url("https://user:password@example.org")


def test_http_error_json_body_is_preserved_for_readiness_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = Message()
    headers["content-type"] = "application/json"
    body = BytesIO(b'{"status":"not_ready","blocking_checks":["database","migrations"]}')

    def _raise_http_error(*_args, **_kwargs):
        raise HTTPError("https://example.org/health/readiness", 503, "Service Unavailable", headers, body)

    monkeypatch.setattr(verifier, "urlopen", _raise_http_error)

    status_code, payload, error = verifier.request_json(
        "https://example.org",
        "/health/readiness",
        1.0,
    )

    assert status_code == 503
    assert payload == {"status": "not_ready", "blocking_checks": ["database", "migrations"]}
    assert error == "HTTP 503"


def test_health_summary_keeps_only_safe_status_and_blocker_names() -> None:
    summary = verifier._health_http_summary(
        503,
        {
            "status": "not_ready",
            "blocking_checks": ["database", "schema", "unsafe check with spaces", "x" * 100],
            "checks": {"database": {"detail": "should-not-be-copied"}},
            "secret": "must-not-be-copied",
        },
        "HTTP 503",
        3,
    )

    assert summary == {
        "status_code": 503,
        "error": "HTTP 503",
        "attempts_used": 3,
        "reported_status": "not_ready",
        "blocking_checks": ["database", "schema"],
    }


def test_transient_timeout_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        [
            (None, None, "TimeoutError"),
            (200, {"status": "ok"}, None),
        ]
    )
    monkeypatch.setattr(verifier, "request_json", lambda *_args, **_kwargs: next(responses))
    delays: list[float] = []

    status_code, payload, error, attempts_used = verifier.request_json_with_retry(
        "https://example.org",
        "/health/live",
        1.0,
        attempts=3,
        retry_delay=0.5,
        sleep_fn=delays.append,
    )

    assert status_code == 200
    assert payload == {"status": "ok"}
    assert error is None
    assert attempts_used == 2
    assert delays == [0.5]


def test_persistent_timeout_exhausts_bounded_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def _timeout(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return None, None, "TimeoutError"

    monkeypatch.setattr(verifier, "request_json", _timeout)

    status_code, payload, error, attempts_used = verifier.request_json_with_retry(
        "https://example.org",
        "/health/readiness",
        1.0,
        attempts=3,
        retry_delay=0,
    )

    assert status_code is None
    assert payload is None
    assert error == "TimeoutError"
    assert attempts_used == 3
    assert calls == 3


def test_permanent_client_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def _not_found(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return 404, None, "HTTP 404"

    monkeypatch.setattr(verifier, "request_json", _not_found)

    status_code, payload, error, attempts_used = verifier.request_json_with_retry(
        "https://example.org",
        "/health/live",
        1.0,
        attempts=3,
        retry_delay=0,
    )

    assert status_code == 404
    assert payload is None
    assert error == "HTTP 404"
    assert attempts_used == 1
    assert calls == 1


def test_transient_http_status_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        [
            (503, {"status": "not_ready", "blocking_checks": ["database"]}, "HTTP 503"),
            (200, {"status": "ready"}, None),
        ]
    )
    monkeypatch.setattr(verifier, "request_json", lambda *_args, **_kwargs: next(responses))

    status_code, payload, error, attempts_used = verifier.request_json_with_retry(
        "https://example.org",
        "/health/readiness",
        1.0,
        attempts=3,
        retry_delay=0,
    )

    assert status_code == 200
    assert payload == {"status": "ready"}
    assert error is None
    assert attempts_used == 2


def test_receipt_records_retry_policy_attempt_usage_and_safe_readiness_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    def _request_with_retry(_base_url, path, _timeout, **_kwargs):
        if path == "/health/live":
            return 200, _live(), None, 2
        return 503, {"status": "not_ready", "blocking_checks": ["database", "migrations"]}, "HTTP 503", 3

    monkeypatch.setattr(verifier, "request_json_with_retry", _request_with_retry)

    receipt = verifier.build_receipt(
        base_url="https://example.org",
        expected_commit=EXPECTED,
        expected_repo_slug="skaba89/CodeRouteGuinee",
        timeout=1.0,
        attempts=3,
        retry_delay=0.25,
    )

    assert receipt["assessment"]["passed"] is False
    assert "READINESS_HTTP_2XX" in receipt["assessment"]["blockers"]
    assert "READINESS_OK" in receipt["assessment"]["blockers"]
    assert receipt["retry_policy"]["attempts"] == 3
    assert receipt["retry_policy"]["retry_delay_seconds"] == 0.25
    assert receipt["http"]["health_live"]["attempts_used"] == 2
    assert receipt["http"]["health_readiness"] == {
        "status_code": 503,
        "error": "HTTP 503",
        "attempts_used": 3,
        "reported_status": "not_ready",
        "blocking_checks": ["database", "migrations"],
    }


def test_cli_rejects_invalid_retry_policy() -> None:
    assert verifier.main(["--attempts", "0"]) == 2
    assert verifier.main(["--retry-delay", "31"]) == 2

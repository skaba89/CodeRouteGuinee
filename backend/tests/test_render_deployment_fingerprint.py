import pytest

from scripts.verify_render_deployment import evaluate_runtime, safe_base_url


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
    result = evaluate_runtime(
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
    result = evaluate_runtime(
        _live("f" * 40),
        {"status": "ready"},
        expected_commit=EXPECTED,
        expected_repo_slug="skaba89/CodeRouteGuinee",
    )
    assert result["passed"] is False
    assert "DEPLOYED_SHA_MATCH" in result["blockers"]


def test_missing_render_commit_is_blocking_even_when_health_is_green() -> None:
    result = evaluate_runtime(
        _live(""),
        {"status": "ready"},
        expected_commit=EXPECTED,
    )
    assert result["passed"] is False
    assert "RENDER_GIT_COMMIT_PRESENT" in result["blockers"]
    assert "DEPLOYED_SHA_MATCH" in result["blockers"]


def test_readiness_failure_is_blocking() -> None:
    result = evaluate_runtime(
        _live(),
        {"status": "not_ready"},
        expected_commit=EXPECTED,
    )
    assert result["passed"] is False
    assert "READINESS_OK" in result["blockers"]


def test_expected_commit_requires_full_sha() -> None:
    with pytest.raises(ValueError):
        evaluate_runtime(_live(), {"status": "ready"}, expected_commit="deadbee")


def test_safe_base_url_rejects_remote_plain_http_and_credentials() -> None:
    assert safe_base_url("https://coderouteguinee-backend.onrender.com/") == "https://coderouteguinee-backend.onrender.com"
    assert safe_base_url("http://localhost:8000") == "http://localhost:8000"
    with pytest.raises(ValueError):
        safe_base_url("http://example.org")
    with pytest.raises(ValueError):
        safe_base_url("https://user:password@example.org")

import importlib.util
import sys
from pathlib import Path


def load_ruleset_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "apply_github_main_ruleset.py"
    spec = importlib.util.spec_from_file_location("apply_github_main_ruleset", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_main_ruleset_payload_is_fail_closed_without_blocking_single_maintainer() -> None:
    ruleset = load_ruleset_module()
    payload = ruleset.build_ruleset_payload()

    assert payload["name"] == "protect-main-release-preflight"
    assert payload["target"] == "branch"
    assert payload["enforcement"] == "active"
    assert payload["bypass_actors"] == []
    assert payload["conditions"] == {
        "ref_name": {"include": ["refs/heads/main"], "exclude": []}
    }

    by_type = {rule["type"]: rule for rule in payload["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request", "required_status_checks"} <= set(by_type)

    pull = by_type["pull_request"]["parameters"]
    assert pull["required_approving_review_count"] == 0
    assert pull["require_last_push_approval"] is False
    assert set(pull["allowed_merge_methods"]) == {"merge", "squash", "rebase"}

    checks = by_type["required_status_checks"]["parameters"]
    assert checks["strict_required_status_checks_policy"] is True
    assert checks["do_not_enforce_on_create"] is False
    assert checks["required_status_checks"] == [{"context": "release-preflight"}]


def test_ruleset_verification_detects_bypass_and_required_check_drift() -> None:
    ruleset = load_ruleset_module()
    expected = ruleset.build_ruleset_payload()
    actual = {
        **expected,
        "id": 42,
        "bypass_actors": [{"actor_id": 1, "actor_type": "User", "bypass_mode": "always"}],
        "rules": [dict(rule) for rule in expected["rules"]],
    }
    actual_rules = {rule["type"]: rule for rule in actual["rules"]}
    actual_rules["required_status_checks"] = {
        "type": "required_status_checks",
        "parameters": {
            "do_not_enforce_on_create": False,
            "required_status_checks": [{"context": "some-other-check"}],
            "strict_required_status_checks_policy": False,
        },
    }
    actual["rules"] = list(actual_rules.values())

    mismatches = ruleset.ruleset_mismatches(actual, expected)

    assert "bypass_actors must be empty" in mismatches
    assert "required_status_checks.parameters.strict_required_status_checks_policy" in mismatches
    assert any("required_status_checks contexts" in item for item in mismatches)


def test_upsert_creates_when_named_ruleset_is_absent() -> None:
    ruleset = load_ruleset_module()
    repository = ruleset.parse_repository("skaba89/CodeRouteGuinee")
    payload = ruleset.build_ruleset_payload()

    class FakeClient:
        def __init__(self):
            self.calls = []

        def request(self, method, path, body=None):
            self.calls.append((method, path, body))
            if method == "GET":
                return []
            if method == "POST":
                return {"id": 123, **body}
            raise AssertionError((method, path))

    client = FakeClient()
    action, applied = ruleset.upsert_ruleset(client, repository, payload)

    assert action == "created"
    assert applied["id"] == 123
    assert [call[0] for call in client.calls] == ["GET", "POST"]


def test_upsert_updates_existing_repository_ruleset() -> None:
    ruleset = load_ruleset_module()
    repository = ruleset.parse_repository("skaba89/CodeRouteGuinee")
    payload = ruleset.build_ruleset_payload()

    class FakeClient:
        def __init__(self):
            self.calls = []

        def request(self, method, path, body=None):
            self.calls.append((method, path, body))
            if method == "GET":
                return [
                    {
                        "id": 77,
                        "name": payload["name"],
                        "source_type": "Repository",
                    }
                ]
            if method == "PUT":
                return {"id": 77, **body}
            raise AssertionError((method, path))

    client = FakeClient()
    action, applied = ruleset.upsert_ruleset(client, repository, payload)

    assert action == "updated"
    assert applied["id"] == 77
    assert client.calls[-1][0] == "PUT"
    assert client.calls[-1][1].endswith("/rulesets/77")


def test_dry_run_never_requires_admin_token(monkeypatch, capsys) -> None:
    ruleset = load_ruleset_module()
    monkeypatch.delenv("GITHUB_ADMIN_TOKEN", raising=False)

    assert ruleset.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert '"release-preflight"' in output
    assert '"refs/heads/main"' in output


def test_apply_fails_closed_without_admin_token(monkeypatch, capsys) -> None:
    ruleset = load_ruleset_module()
    monkeypatch.delenv("GITHUB_ADMIN_TOKEN", raising=False)

    assert ruleset.main(["--apply"]) == 2
    assert "Administration: write" in capsys.readouterr().err

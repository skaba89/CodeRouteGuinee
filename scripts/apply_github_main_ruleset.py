#!/usr/bin/env python3
"""Provision and verify the CodeRoute GitHub ruleset protecting ``main``.

Apply/check modes require a token with repository Administration (write).
``--dry-run`` never calls GitHub and never requires a token.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_REPOSITORY = "skaba89/CodeRouteGuinee"
DEFAULT_BRANCH = "main"
DEFAULT_REQUIRED_CHECK = "release-preflight"
DEFAULT_RULESET_NAME = "protect-main-release-preflight"
GITHUB_API_URL = "https://api.github.com"
API_VERSION = "2026-03-10"


class RulesetError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepositoryRef:
    owner: str
    repo: str


def parse_repository(value: str) -> RepositoryRef:
    parts = [part.strip() for part in (value or "").split("/") if part.strip()]
    if len(parts) != 2:
        raise ValueError("repository must use owner/name format")
    owner, repo = parts
    if any(char in owner + repo for char in "?#"):
        raise ValueError("repository contains invalid URL characters")
    return RepositoryRef(owner=owner, repo=repo)


def build_ruleset_payload(
    *,
    branch: str = DEFAULT_BRANCH,
    required_check: str = DEFAULT_REQUIRED_CHECK,
    ruleset_name: str = DEFAULT_RULESET_NAME,
) -> dict[str, Any]:
    branch = branch.strip()
    required_check = required_check.strip()
    ruleset_name = ruleset_name.strip()
    if not branch or branch.startswith("refs/"):
        raise ValueError("branch must be a simple branch name")
    if not required_check:
        raise ValueError("required check must not be empty")
    if not ruleset_name:
        raise ValueError("ruleset name must not be empty")

    return {
        "name": ruleset_name,
        "target": "branch",
        "enforcement": "active",
        # No silent admin/user/app bypass. Emergency overrides must be added
        # explicitly and therefore remain visible in GitHub's audit trail.
        "bypass_actors": [],
        "conditions": {
            "ref_name": {
                "include": [f"refs/heads/{branch}"],
                "exclude": [],
            }
        },
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {
                "type": "pull_request",
                "parameters": {
                    "allowed_merge_methods": ["merge", "squash", "rebase"],
                    "dismiss_stale_reviews_on_push": False,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_approving_review_count": 0,
                    "required_review_thread_resolution": False,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "do_not_enforce_on_create": False,
                    "required_status_checks": [{"context": required_check}],
                    "strict_required_status_checks_policy": True,
                },
            },
        ],
    }


def _rule_map(ruleset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        return {}
    return {
        str(rule.get("type")): rule
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("type"), str)
    }


def ruleset_mismatches(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    """Return differences for the security-critical policy subset."""
    mismatches: list[str] = []
    for key in ("name", "target", "enforcement"):
        if actual.get(key) != expected.get(key):
            mismatches.append(f"{key}: expected={expected.get(key)!r} actual={actual.get(key)!r}")

    expected_conditions = expected["conditions"]["ref_name"]
    actual_conditions = actual.get("conditions", {}).get("ref_name", {})
    if actual_conditions.get("include") != expected_conditions["include"]:
        mismatches.append("conditions.ref_name.include")
    if actual_conditions.get("exclude", []) != expected_conditions["exclude"]:
        mismatches.append("conditions.ref_name.exclude")

    if actual.get("bypass_actors", []) != []:
        mismatches.append("bypass_actors must be empty")

    actual_rules = _rule_map(actual)
    expected_rules = _rule_map(expected)
    for required_type in ("deletion", "non_fast_forward", "pull_request", "required_status_checks"):
        if required_type not in actual_rules:
            mismatches.append(f"missing rule: {required_type}")

    pull = actual_rules.get("pull_request", {}).get("parameters", {})
    expected_pull = expected_rules["pull_request"]["parameters"]
    for key, value in expected_pull.items():
        if pull.get(key) != value:
            mismatches.append(f"pull_request.parameters.{key}")

    checks = actual_rules.get("required_status_checks", {}).get("parameters", {})
    if checks.get("strict_required_status_checks_policy") is not True:
        mismatches.append("required_status_checks.parameters.strict_required_status_checks_policy")
    if checks.get("do_not_enforce_on_create") is not False:
        mismatches.append("required_status_checks.parameters.do_not_enforce_on_create")
    actual_contexts = [
        item.get("context")
        for item in checks.get("required_status_checks", [])
        if isinstance(item, dict)
    ]
    expected_contexts = [
        item["context"]
        for item in expected_rules["required_status_checks"]["parameters"]["required_status_checks"]
    ]
    if actual_contexts != expected_contexts:
        mismatches.append(
            f"required_status_checks contexts: expected={expected_contexts!r} actual={actual_contexts!r}"
        )
    return mismatches


class GitHubRulesClient:
    def __init__(self, *, token: str, timeout: float = 20.0) -> None:
        token = token.strip()
        if not token:
            raise ValueError("GitHub admin token is required")
        self.token = token
        self.timeout = timeout

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{GITHUB_API_URL}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "CodeRoute-Main-Ruleset-Provisioner/1.0",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                raw = response.read(1_000_000)
        except HTTPError as exc:
            try:
                body = exc.read(100_000).decode("utf-8", errors="replace")
            except OSError:
                body = ""
            raise RulesetError(f"GitHub API HTTP {exc.code}: {body[:1000]}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RulesetError(f"GitHub API request failed: {exc.__class__.__name__}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RulesetError("GitHub API returned invalid JSON") from exc


def _base_path(repository: RepositoryRef) -> str:
    return f"/repos/{quote(repository.owner, safe='')}/{quote(repository.repo, safe='')}"


def find_ruleset(client: GitHubRulesClient, repository: RepositoryRef, name: str) -> dict[str, Any] | None:
    response = client.request("GET", f"{_base_path(repository)}/rulesets?includes_parents=false")
    if not isinstance(response, list):
        raise RulesetError("GitHub ruleset list response is not an array")
    for item in response:
        if isinstance(item, dict) and item.get("name") == name and item.get("source_type") == "Repository":
            return item
    return None


def get_ruleset(client: GitHubRulesClient, repository: RepositoryRef, ruleset_id: int) -> dict[str, Any]:
    response = client.request("GET", f"{_base_path(repository)}/rulesets/{ruleset_id}?includes_parents=false")
    if not isinstance(response, dict):
        raise RulesetError("GitHub ruleset response is not an object")
    return response


def upsert_ruleset(
    client: GitHubRulesClient,
    repository: RepositoryRef,
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    existing = find_ruleset(client, repository, str(payload["name"]))
    if existing is None:
        response = client.request("POST", f"{_base_path(repository)}/rulesets", payload)
        action = "created"
    else:
        ruleset_id = int(existing["id"])
        response = client.request("PUT", f"{_base_path(repository)}/rulesets/{ruleset_id}", payload)
        action = "updated"
    if not isinstance(response, dict) or not isinstance(response.get("id"), int):
        raise RulesetError("GitHub did not return a valid ruleset after apply")
    return action, response


def verify_ruleset(
    client: GitHubRulesClient,
    repository: RepositoryRef,
    expected: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    summary = find_ruleset(client, repository, str(expected["name"]))
    if summary is None:
        return None, ["ruleset not found"]
    actual = get_ruleset(client, repository, int(summary["id"]))
    return actual, ruleset_mismatches(actual, expected)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply or verify the CodeRoute main branch GitHub ruleset")
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", DEFAULT_REPOSITORY))
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--required-check", default=DEFAULT_REQUIRED_CHECK)
    parser.add_argument("--ruleset-name", default=DEFAULT_RULESET_NAME)
    parser.add_argument("--token-env", default="GITHUB_ADMIN_TOKEN")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repository = parse_repository(args.repository)
        payload = build_ruleset_payload(
            branch=args.branch,
            required_check=args.required_check,
            ruleset_name=args.ruleset_name,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    token = os.getenv(args.token_env, "")
    if not token:
        print(
            f"ERROR: {args.token_env} is required and must have repository Administration: write permission",
            file=sys.stderr,
        )
        return 2

    try:
        client = GitHubRulesClient(token=token)
        if args.apply:
            action, applied = upsert_ruleset(client, repository, payload)
            print(f"Ruleset {action}: id={applied['id']} name={applied.get('name')}")
        actual, mismatches = verify_ruleset(client, repository, payload)
    except (RulesetError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if actual is None or mismatches:
        print("ERROR: main protection ruleset is not compliant", file=sys.stderr)
        for mismatch in mismatches:
            print(f" - {mismatch}", file=sys.stderr)
        return 2

    print(
        "GitHub main protection verified: "
        f"ruleset_id={actual['id']} enforcement={actual.get('enforcement')} "
        f"branch={args.branch} required_check={args.required_check}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

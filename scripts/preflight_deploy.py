import argparse
import os
import sys
import urllib.error
import urllib.request


PLACEHOLDER_VALUES = {
    "change-me-in-production",
    "replace-with-a-long-random-production-secret",
    "replace-with-a-private-bootstrap-token",
    "replace-with-a-strong-postgres-password",
    "replace-with-a-strong-temporary-password",
    "coderoute",
}


def parse_env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip().lstrip("\ufeff")] = value.strip().strip('"').strip("'")
    return values


def is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def add_issue(issues: list[str], condition: bool, message: str) -> None:
    if condition:
        issues.append(message)


def validate_env(values: dict[str, str], target: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    is_production = target == "production"

    environment = values.get("ENVIRONMENT", "")
    add_issue(errors, not environment, "ENVIRONMENT is required")
    if is_production:
        add_issue(errors, environment.lower() != "production", "ENVIRONMENT must be production")

    secret_key = values.get("SECRET_KEY", "")
    add_issue(errors, not secret_key or secret_key in PLACEHOLDER_VALUES, "SECRET_KEY must be replaced")
    add_issue(warnings, bool(secret_key) and len(secret_key) < 32, "SECRET_KEY should contain at least 32 characters")

    admin_token = values.get("ADMIN_REGISTRATION_TOKEN", "")
    add_issue(errors, not admin_token or admin_token in PLACEHOLDER_VALUES, "ADMIN_REGISTRATION_TOKEN must be private and non-placeholder")

    database_url = values.get("DATABASE_URL", "")
    add_issue(errors, not database_url, "DATABASE_URL is required")
    add_issue(errors if is_production else warnings, database_url.startswith("sqlite"), "DATABASE_URL should use PostgreSQL")

    auto_create_tables = values.get("AUTO_CREATE_TABLES")
    add_issue(errors if is_production else warnings, is_truthy(auto_create_tables), "AUTO_CREATE_TABLES must be false outside development")

    cors_origins = [origin.strip() for origin in values.get("CORS_ORIGINS", "").split(",") if origin.strip()]
    add_issue(errors, not cors_origins, "CORS_ORIGINS must contain official frontend origins")
    add_issue(errors, "*" in cors_origins, "CORS_ORIGINS must not contain wildcard origin")
    if is_production:
        add_issue(
            errors,
            any("localhost" in origin or "127.0.0.1" in origin for origin in cors_origins),
            "CORS_ORIGINS must not contain local origins in production",
        )
        add_issue(errors, any(not origin.startswith("https://") for origin in cors_origins), "CORS_ORIGINS must use HTTPS in production")

    postgres_password = values.get("POSTGRES_PASSWORD", "")
    add_issue(errors, not postgres_password or postgres_password in PLACEHOLDER_VALUES, "POSTGRES_PASSWORD must be replaced")

    bootstrap_password = values.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    add_issue(errors, not bootstrap_password or bootstrap_password in PLACEHOLDER_VALUES, "BOOTSTRAP_ADMIN_PASSWORD must be replaced")
    add_issue(warnings, bool(bootstrap_password) and len(bootstrap_password) < 12, "BOOTSTRAP_ADMIN_PASSWORD should contain at least 12 characters")

    bootstrap_email = values.get("BOOTSTRAP_ADMIN_EMAIL", "")
    add_issue(warnings, not bootstrap_email, "BOOTSTRAP_ADMIN_EMAIL is recommended for first admin creation")

    vite_api_base = values.get("VITE_API_BASE_URL", "")
    if is_production and vite_api_base:
        add_issue(errors, not vite_api_base.startswith("https://"), "VITE_API_BASE_URL must use HTTPS in production")

    return errors, warnings


def check_readiness(api_url: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with urllib.request.urlopen(f"{api_url.rstrip('/')}/health/readiness", timeout=10) as response:
            body = response.read().decode("utf-8", "replace")
            if response.status != 200:
                errors.append(f"readiness returned HTTP {response.status}")
            if '"status":"error"' in body or '"status": "error"' in body:
                errors.append("readiness contains an error check")
            if '"status":"warning"' in body or '"status": "warning"' in body:
                warnings.append("readiness contains a warning check")
            if '"configuration"' not in body:
                warnings.append("readiness response does not expose configuration check")
    except urllib.error.HTTPError as exc:
        errors.append(f"readiness HTTP error {exc.code}")
    except urllib.error.URLError as exc:
        errors.append(f"readiness unavailable: {exc.reason}")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="CodeRoute Guinee deployment preflight")
    parser.add_argument("--env-file", default=".env", help="Path to the env file to validate")
    parser.add_argument("--target", choices=["staging", "production"], default="production")
    parser.add_argument("--api-url", default="", help="Optional API base URL to validate /health/readiness")
    args = parser.parse_args()

    if not os.path.exists(args.env_file):
        print(f"ERROR - env file not found: {args.env_file}", file=sys.stderr)
        return 1

    values = parse_env_file(args.env_file)
    errors, warnings = validate_env(values, args.target)
    if args.api_url:
        readiness_errors, readiness_warnings = check_readiness(args.api_url)
        errors.extend(readiness_errors)
        warnings.extend(readiness_warnings)

    print(f"CodeRoute Guinee preflight - target={args.target}")
    for warning in warnings:
        print(f"WARN - {warning}")
    for error in errors:
        print(f"ERROR - {error}")

    if errors:
        print(f"Preflight failed with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("Preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

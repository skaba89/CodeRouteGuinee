import importlib.util
from pathlib import Path


def load_preflight_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "preflight_deploy.py"
    spec = importlib.util.spec_from_file_location("preflight_deploy", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_preflight_rejects_placeholder_production_values() -> None:
    preflight = load_preflight_module()
    errors, warnings = preflight.validate_env(
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "change-me-in-production",
            "ADMIN_REGISTRATION_TOKEN": "replace-with-a-private-bootstrap-token",
            "DATABASE_URL": "sqlite:///./coderoute.db",
            "AUTO_CREATE_TABLES": "true",
            "CORS_ORIGINS": "http://localhost:5173,*",
            "ALLOWED_HOSTS": "localhost,*",
            "ENABLE_API_DOCS": "true",
            "POSTGRES_PASSWORD": "coderoute",
            "BOOTSTRAP_ADMIN_PASSWORD": "replace-with-a-strong-temporary-password",
            "VITE_API_BASE_URL": "http://localhost:8000",
        },
        "production",
    )

    assert "SECRET_KEY should contain at least 32 characters" in warnings
    assert "BOOTSTRAP_ADMIN_EMAIL is recommended for first admin creation" in warnings
    assert "SECRET_KEY must be replaced" in errors
    assert "ADMIN_REGISTRATION_TOKEN must be private and non-placeholder" in errors
    assert "DATABASE_URL should use PostgreSQL" in errors
    assert "AUTO_CREATE_TABLES must be false outside development" in errors
    assert "CORS_ORIGINS must not contain wildcard origin" in errors
    assert "CORS_ORIGINS must not contain local origins in production" in errors
    assert "ALLOWED_HOSTS must not contain wildcard host" in errors
    assert "ALLOWED_HOSTS must not contain local hosts in production" in errors
    assert "ENABLE_API_DOCS must be false in production" in errors
    assert "POSTGRES_PASSWORD must be replaced" in errors
    assert "BOOTSTRAP_ADMIN_PASSWORD must be replaced" in errors
    assert "VITE_API_BASE_URL must use HTTPS in production" in errors


def test_preflight_accepts_hardened_production_values() -> None:
    preflight = load_preflight_module()
    errors, warnings = preflight.validate_env(
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "prod-secret-key-with-more-than-32-characters",
            "ADMIN_REGISTRATION_TOKEN": "private-admin-bootstrap-token",
            "DATABASE_URL": "postgresql+psycopg://coderoute:strong@postgres:5432/coderoute",
            "AUTO_CREATE_TABLES": "false",
            "CORS_ORIGINS": "https://coderoute.gov.gn,https://admin.coderoute.gov.gn",
            "ALLOWED_HOSTS": "api.coderoute.gov.gn",
            "ENABLE_API_DOCS": "false",
            "POSTGRES_PASSWORD": "strong-postgres-password-not-default",
            "BOOTSTRAP_ADMIN_EMAIL": "admin@coderoute.gov.gn",
            "BOOTSTRAP_ADMIN_PASSWORD": "strong-bootstrap-password",
            "VITE_API_BASE_URL": "https://api.coderoute.gov.gn",
        },
        "production",
    )

    assert errors == []
    assert warnings == []


def test_preflight_parses_utf8_bom_env_file(tmp_path) -> None:
    preflight = load_preflight_module()
    env_file = tmp_path / "production.env"
    env_file.write_text("\ufeffENVIRONMENT=production\nSECRET_KEY='abc'\n", encoding="utf-8")

    values = preflight.parse_env_file(str(env_file))

    assert values["ENVIRONMENT"] == "production"
    assert values["SECRET_KEY"] == "abc"

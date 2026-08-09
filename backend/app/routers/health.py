from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.distributed import check_shared_state, instance_id

router = APIRouter(tags=["health"])
settings = get_settings()

CRITICAL_TABLES = {"users", "candidates", "centers", "exam_sessions", "bookings", "payments", "audit_logs"}


def _build_configuration_check(current_settings) -> dict:
    environment = current_settings.environment.lower()
    is_production = environment == "production"
    errors: list[str] = []
    warnings: list[str] = []
    placeholders = {
        "change-me-in-production", "replace-with-a-long-random-production-secret",
        "CHANGE_ME_secret_key_must_be_set_in_env", "CHANGE_ME_database_url_must_be_set_in_env",
        "", "changeme", "your-secret",
    }

    if current_settings.secret_key in placeholders or current_settings.secret_key.startswith("CHANGE_ME"):
        (errors if is_production else warnings).append("SECRET_KEY must be replaced (placeholder detected)")
    elif len(current_settings.secret_key) < 32:
        warnings.append("SECRET_KEY should contain at least 32 characters")
    if current_settings.database_url in placeholders or current_settings.database_url.startswith("CHANGE_ME"):
        (errors if is_production else warnings).append("DATABASE_URL must be set")
    if current_settings.database_url.startswith("sqlite"):
        (errors if is_production else warnings).append("DATABASE_URL should use PostgreSQL outside local development")
    if current_settings.auto_create_tables:
        (errors if is_production else warnings).append("AUTO_CREATE_TABLES must be false outside local development")

    origins = current_settings.cors_origin_list
    if not origins:
        (errors if is_production else warnings).append("CORS_ORIGINS must contain at least one origin")
    if "*" in origins:
        (errors if is_production else warnings).append("CORS_ORIGINS must not contain wildcard origin")
    if is_production and any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
        errors.append("CORS_ORIGINS must not contain local origins in production")

    allowed_hosts = current_settings.allowed_host_list
    if not allowed_hosts:
        (errors if is_production else warnings).append("ALLOWED_HOSTS must contain at least one host")
    if "*" in allowed_hosts:
        (errors if is_production else warnings).append("ALLOWED_HOSTS must not contain wildcard host in production")
    if is_production and any(host in {"localhost", "127.0.0.1", "testserver"} for host in allowed_hosts):
        errors.append("ALLOWED_HOSTS must not contain local hosts in production")

    if is_production and current_settings.enable_api_docs:
        errors.append("ENABLE_API_DOCS must be false in production")
    if is_production and not current_settings.admin_registration_token:
        errors.append("ADMIN_REGISTRATION_TOKEN is required in production")

    ha_mode = bool(getattr(current_settings, "ha_mode", False))
    redis_required = bool(getattr(current_settings, "redis_required", False))
    redis_url = str(getattr(current_settings, "redis_url", "") or "").strip()
    expected_instances = int(getattr(current_settings, "expected_api_instances", 1) or 1)
    if (ha_mode or redis_required) and not redis_url:
        errors.append("REDIS_URL is required when HA_MODE or REDIS_REQUIRED is enabled")
    if redis_url and not redis_url.startswith(("redis://", "rediss://")):
        errors.append("REDIS_URL must use redis:// or rediss://")
    if ha_mode and expected_instances < 2:
        errors.append("EXPECTED_API_INSTANCES must be >= 2 when HA_MODE is enabled")

    return {
        "status": "error" if errors else "warning" if warnings else "ok",
        "environment": environment,
        "errors": errors,
        "warnings": warnings,
        "cors_origins_count": len(origins),
        "allowed_hosts_count": len(allowed_hosts),
        "api_docs_enabled": current_settings.enable_api_docs,
        "ha_mode": ha_mode,
        "expected_api_instances": expected_instances,
    }


def _runtime_metadata() -> dict:
    return {
        "instance_id": instance_id(),
        "deployment_id": str(getattr(settings, "deployment_id", "") or "") or None,
        "ha_mode": bool(getattr(settings, "ha_mode", False)),
        "expected_api_instances": int(getattr(settings, "expected_api_instances", 1) or 1),
    }


@router.get("/health")
@router.get("/health/live")
def health() -> dict:
    from app.api import API_VERSION
    return {"status": "ok", "service": settings.project_name, "version": API_VERSION, "environment": settings.environment, "runtime": _runtime_metadata()}


@router.get("/health/readiness")
def readiness(response: Response, db: Session = Depends(get_db)) -> dict:
    checks: dict[str, dict] = {
        "configuration": _build_configuration_check(settings),
        "database": {"status": "unknown"},
        "schema": {"status": "unknown"},
        "migrations": {"status": "unknown"},
        "shared_state": check_shared_state(),
    }
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": exc.__class__.__name__}

    try:
        inspector = inspect(db.bind)
        tables = set(inspector.get_table_names())
        missing_tables = sorted(CRITICAL_TABLES - tables)
        checks["schema"] = {"status": "ok" if not missing_tables else "error", "critical_tables": sorted(CRITICAL_TABLES), "missing_tables": missing_tables}
        if "alembic_version" in tables:
            version = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            checks["migrations"] = {"status": "ok" if version else "warning", "version": version}
        else:
            checks["migrations"] = {"status": "warning" if settings.auto_create_tables else "error", "version": None, "detail": "alembic_version table not found"}
    except Exception as exc:
        checks["schema"] = {"status": "error", "detail": exc.__class__.__name__}
        checks["migrations"] = {"status": "error", "detail": exc.__class__.__name__}

    blocking_checks = [name for name, check in checks.items() if check.get("status") == "error"]
    overall = "not_ready" if blocking_checks else "ready"
    if blocking_checks:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": overall, "service": settings.project_name, "runtime": _runtime_metadata(), "blocking_checks": blocking_checks, "checks": checks}

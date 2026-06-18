from fastapi import APIRouter, Depends
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])
settings = get_settings()

CRITICAL_TABLES = {
    "users",
    "candidates",
    "centers",
    "exam_sessions",
    "bookings",
    "payments",
    "audit_logs",
}


def _build_configuration_check(current_settings) -> dict:
    environment = current_settings.environment.lower()
    is_production = environment == "production"
    errors: list[str] = []
    warnings: list[str] = []

    if current_settings.secret_key in {"change-me-in-production", "replace-with-a-long-random-production-secret"}:
        errors.append("SECRET_KEY must be replaced")
    elif len(current_settings.secret_key) < 32:
        warnings.append("SECRET_KEY should contain at least 32 characters")

    if current_settings.database_url.startswith("sqlite"):
        (errors if is_production else warnings).append("DATABASE_URL should use PostgreSQL outside local development")

    if current_settings.auto_create_tables:
        (errors if is_production else warnings).append("AUTO_CREATE_TABLES must be false outside local development")

    origins = current_settings.cors_origin_list
    if not origins:
        errors.append("CORS_ORIGINS must contain at least one origin")
    if "*" in origins:
        errors.append("CORS_ORIGINS must not contain wildcard origin")
    if is_production and any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
        errors.append("CORS_ORIGINS must not contain local origins in production")

    if is_production and not current_settings.admin_registration_token:
        errors.append("ADMIN_REGISTRATION_TOKEN is required in production")

    if is_production and not current_settings.bootstrap_admin_email:
        warnings.append("BOOTSTRAP_ADMIN_EMAIL is recommended for controlled first admin creation")

    status = "error" if errors else "warning" if warnings else "ok"
    return {
        "status": status,
        "environment": environment,
        "errors": errors,
        "warnings": warnings,
        "cors_origins_count": len(origins),
    }


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.project_name}


@router.get("/health/readiness")
def readiness(db: Session = Depends(get_db)) -> dict:
    checks: dict[str, dict] = {
        "configuration": _build_configuration_check(settings),
        "database": {"status": "unknown"},
        "schema": {"status": "unknown"},
        "migrations": {"status": "unknown"},
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
        checks["schema"] = {
            "status": "ok" if not missing_tables else "error",
            "critical_tables": sorted(CRITICAL_TABLES),
            "missing_tables": missing_tables,
        }
        if "alembic_version" in tables:
            version = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            checks["migrations"] = {"status": "ok" if version else "warning", "version": version}
        else:
            checks["migrations"] = {
                "status": "warning" if settings.auto_create_tables else "error",
                "version": None,
                "detail": "alembic_version table not found",
            }
    except Exception as exc:
        checks["schema"] = {"status": "error", "detail": exc.__class__.__name__}
        checks["migrations"] = {"status": "error", "detail": exc.__class__.__name__}

    overall = "ready" if all(check["status"] == "ok" for check in checks.values()) else "degraded"
    return {"status": overall, "service": settings.project_name, "checks": checks}

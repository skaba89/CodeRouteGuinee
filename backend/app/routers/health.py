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


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.project_name}


@router.get("/health/readiness")
def readiness(db: Session = Depends(get_db)) -> dict:
    checks: dict[str, dict] = {
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

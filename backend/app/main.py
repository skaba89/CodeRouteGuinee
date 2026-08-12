import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError as _ValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import JSONResponse as _JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.media_quality import MediaApprovalBlocked
from app.reliability_config import get_reliability_settings
from app.soc_config import get_soc_settings

try:
    _startup_settings = get_settings()
    _startup_settings.validate_production_secrets()
    get_reliability_settings().validate(production=_startup_settings.is_production)
    get_soc_settings().validate(production=_startup_settings.is_production)
except RuntimeError as _e:
    import logging as _log
    _log.getLogger("coderoute.startup").critical(str(_e))
    raise

from app.audit_chain import ensure_audit_chain_anchor
from app.core.config import get_settings as _get_settings
from app.db.session import SessionLocal, init_db
from app.logging_config import setup_logging
from app.middleware import GlobalRateLimitMiddleware, RequestIDMiddleware, ResponseCacheMiddleware, TimingMiddleware
from app.monitoring import capture_exception as capture_monitoring_exception
from app.reliability_metrics import ReliabilityMetricsMiddleware
from app.soc_logging import install_soc_log_filter
from app.soc_telemetry import SOCRequestMiddleware, init_soc_telemetry
from app.routers import (
    audio,
    audit,
    auth,
    bookings,
    candidate_identity,
    candidate_submissions,
    candidates,
    center_edge,
    center_incidents,
    center_stations,
    centers,
    dashboard,
    device_sessions,
    documents,
    entries,
    exam_media_questions,
    exam_monitoring,
    exam_question_traces,
    exam_reviews,
    exam_runtime,
    exams,
    health,
    institutional_authorizations,
    media_library,
    media_reviews,
    metrics,
    national_governance,
    operations,
    payment_reconciliation,
    payments,
    question_governance,
    questions,
    reliability,
    security_operations,
    sessions,
    supervision,
    training,
    users,
)
from app.routers.elearning import router_admin as elearning_admin_router
from app.routers.elearning import router_public as elearning_public_router
from app.routers.rgpd import router as rgpd_router
from app.routers.tarifs import router_admin as tarifs_admin_router
from app.routers.tarifs import router_public as tarifs_public_router

settings = get_settings()
setup_logging()
install_soc_log_filter()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_sentry(
        dsn=settings.sentry_dsn or None,
        environment=settings.sentry_environment or settings.environment,
        release="0.14.0",
        traces_sample_rate=settings.sentry_sample_rate,
    )
    init_soc_telemetry()
    try:
        init_db()
    except Exception as e:
        import logging
        logging.getLogger("app.startup").warning(
            "init_db() non-critique ignoré au démarrage: %s", e
        )
    if get_soc_settings().audit_chain_enabled:
        db = SessionLocal()
        try:
            ensure_audit_chain_anchor(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.project_name,
    description="Plateforme nationale d'examen du code de la route en Guinee",
    version="0.14.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

_settings = _get_settings()
app.add_middleware(ResponseCacheMiddleware, environment=_settings.environment)
app.add_middleware(ReliabilityMetricsMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(SOCRequestMiddleware)
app.add_middleware(RequestIDMiddleware)

from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)

if _settings.environment.lower() == "production":
    app.add_middleware(GlobalRateLimitMiddleware, max_requests=300, window_seconds=60)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_host_list,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if settings.environment.lower() == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


app.add_middleware(SecurityHeadersMiddleware)

if os.environ.get("ENVIRONMENT", "development").lower() == "production":
    from app.csrf import check_csrf as _check_csrf

    class _CsrfMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            try:
                _check_csrf(request)
            except Exception as exc:
                return JSONResponse({"detail": str(exc)}, status_code=403)
            return await call_next(request)

    app.add_middleware(_CsrfMiddleware)


def _cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin", "")
    allowed = settings.cors_origin_list
    if origin in allowed or "*" in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-CSRF-Token",
        }
    return {}


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    value = getattr(route, "path", None)
    return value[:160] if isinstance(value, str) and value else "unmatched"


@app.exception_handler(MediaApprovalBlocked)
async def media_approval_blocked_handler(_req: Request, exc: MediaApprovalBlocked) -> _JSONResponse:
    return _JSONResponse(
        status_code=409,
        content={
            "detail": {
                "code": "MEDIA_QUALITY_GATE_BLOCKED",
                "message": str(exc),
                "assessment": exc.assessment,
            }
        },
        headers=_cors_headers(_req),
    )


@app.exception_handler(Exception)
async def global_exception_handler(_req: Request, exc: Exception) -> _JSONResponse:
    route = _route_template(_req)
    request_id = getattr(_req.state, "request_id", None)
    capture_monitoring_exception(
        exc,
        context={
            "method": _req.method,
            "route": route,
            "request_id": request_id,
        },
    )
    import logging as _log
    _log.getLogger("coderoute.errors").error(
        "Erreur 500 non gérée %s %s : %s",
        _req.method,
        route,
        exc,
        extra={"method": _req.method, "route": route, "request_id": request_id},
        exc_info=True,
    )
    return _JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur. L'équipe technique a été notifiée."},
        headers=_cors_headers(_req),
    )


@app.exception_handler(_ValidationError)
async def validation_exception_handler(_req: Request, exc: _ValidationError) -> _JSONResponse:
    errors = []
    for err in exc.errors():
        field = " → ".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg", "Valeur invalide")})
    return _JSONResponse(
        status_code=422,
        content={"detail": "Données invalides", "errors": errors},
        headers=_cors_headers(_req),
    )


def _install_media_aware_exam_questions_route() -> None:
    """Replace only the candidate question GET route, preserving its public URL."""
    replacement = next(
        route
        for route in exam_media_questions.router.routes
        if getattr(route, "path", None) == "/exams/{attempt_id}/questions"
        and "GET" in (getattr(route, "methods", None) or set())
    )
    for index, route in enumerate(exams.router.routes):
        if (
            getattr(route, "path", None) == "/exams/{attempt_id}/questions"
            and "GET" in (getattr(route, "methods", None) or set())
        ):
            exams.router.routes[index] = replacement
            return
    raise RuntimeError("Exam questions route not found")


_install_media_aware_exam_questions_route()

app.include_router(metrics.router)
app.include_router(audio.router, prefix=settings.api_v1_prefix)
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(candidates.router, prefix=settings.api_v1_prefix)
app.include_router(candidate_identity.router, prefix=settings.api_v1_prefix)
app.include_router(centers.router, prefix=settings.api_v1_prefix)
app.include_router(questions.router, prefix=settings.api_v1_prefix)
app.include_router(media_library.router, prefix=settings.api_v1_prefix)
app.include_router(media_reviews.router, prefix=settings.api_v1_prefix)
app.include_router(question_governance.router, prefix=settings.api_v1_prefix)
app.include_router(sessions.router, prefix=settings.api_v1_prefix)
app.include_router(exams.router, prefix=settings.api_v1_prefix)
app.include_router(exam_runtime.router, prefix=settings.api_v1_prefix)
app.include_router(institutional_authorizations.router, prefix=settings.api_v1_prefix)
app.include_router(bookings.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)
app.include_router(payments.router, prefix=settings.api_v1_prefix)
app.include_router(payment_reconciliation.router, prefix=settings.api_v1_prefix)
app.include_router(operations.router, prefix=settings.api_v1_prefix)
app.include_router(reliability.router, prefix=settings.api_v1_prefix)
app.include_router(national_governance.router, prefix=settings.api_v1_prefix)
app.include_router(security_operations.router, prefix=settings.api_v1_prefix)
app.include_router(entries.router, prefix=settings.api_v1_prefix)
app.include_router(center_incidents.router, prefix=settings.api_v1_prefix)
app.include_router(center_stations.router, prefix=settings.api_v1_prefix)
app.include_router(center_edge.router, prefix=settings.api_v1_prefix)
app.include_router(device_sessions.router, prefix=settings.api_v1_prefix)
app.include_router(exam_monitoring.router, prefix=settings.api_v1_prefix)
app.include_router(exam_reviews.router, prefix=settings.api_v1_prefix)
app.include_router(exam_question_traces.router, prefix=settings.api_v1_prefix)
app.include_router(candidate_submissions.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(audit.router, prefix=settings.api_v1_prefix)
app.include_router(training.router, prefix=settings.api_v1_prefix)
app.include_router(supervision.router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)

app.include_router(elearning_public_router, prefix=settings.api_v1_prefix)
app.include_router(elearning_admin_router, prefix=settings.api_v1_prefix)
app.include_router(rgpd_router, prefix=settings.api_v1_prefix)
app.include_router(tarifs_public_router, prefix=settings.api_v1_prefix)
app.include_router(tarifs_admin_router, prefix=settings.api_v1_prefix)

from app.routers.admin_ops import router as admin_ops_router
app.include_router(admin_ops_router, prefix=settings.api_v1_prefix)

from app.routers.registration import router as registration_router
app.include_router(registration_router, prefix=settings.api_v1_prefix)

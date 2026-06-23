import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.core.config import get_settings as _get_settings
from app.db.session import init_db
from app.logging_config import setup_logging
from app.middleware import RequestIDMiddleware, ResponseCacheMiddleware, TimingMiddleware
from app.monitoring import init_sentry
from app.routers import (
    audio,
    audit,
    auth,
    bookings,
    candidate_identity,
    candidate_submissions,
    candidates,
    center_incidents,
    center_stations,
    centers,
    dashboard,
    device_sessions,
    documents,
    entries,
    exam_monitoring,
    exam_question_traces,
    exam_reviews,
    exams,
    health,
    institutional_authorizations,
    operations,
    payment_reconciliation,
    payments,
    question_governance,
    questions,
    sessions,
    supervision,
    training,
    users,
)

settings = get_settings()


# Initialiser le logging structuré
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_sentry(
        dsn=settings.sentry_dsn or None,
        environment=settings.sentry_environment or settings.environment,
        release="0.14.0",
        traces_sample_rate=settings.sentry_sample_rate,
    )
    init_db()
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

# ── Fichiers statiques — audio questions ──────────────────────────────────────
_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# ── Middleware — ordre : externe → interne ────────────────────────────────────
# L'ordre d'enregistrement est inversé : le dernier ajouté s'exécute en premier
_settings = _get_settings()
app.add_middleware(ResponseCacheMiddleware, environment=_settings.environment)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)

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


# ── Middleware CSRF — actif uniquement en production ──────────────────────────
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


app.include_router(audio.router, prefix=settings.api_v1_prefix)
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(candidates.router, prefix=settings.api_v1_prefix)
app.include_router(candidate_identity.router, prefix=settings.api_v1_prefix)
app.include_router(centers.router, prefix=settings.api_v1_prefix)
app.include_router(questions.router, prefix=settings.api_v1_prefix)
app.include_router(question_governance.router, prefix=settings.api_v1_prefix)
app.include_router(sessions.router, prefix=settings.api_v1_prefix)
app.include_router(exams.router, prefix=settings.api_v1_prefix)
app.include_router(institutional_authorizations.router, prefix=settings.api_v1_prefix)
app.include_router(bookings.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)
app.include_router(payments.router, prefix=settings.api_v1_prefix)
app.include_router(payment_reconciliation.router, prefix=settings.api_v1_prefix)
app.include_router(operations.router, prefix=settings.api_v1_prefix)
app.include_router(entries.router, prefix=settings.api_v1_prefix)
app.include_router(center_incidents.router, prefix=settings.api_v1_prefix)
app.include_router(center_stations.router, prefix=settings.api_v1_prefix)
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

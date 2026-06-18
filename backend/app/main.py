from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.db.session import init_db
from app.routers import auth, bookings, candidates, candidate_identity, candidate_submissions, center_incidents, center_stations, centers, dashboard, device_sessions, documents, entries, exam_monitoring, exam_question_traces, exam_reviews, exams, health, institutional_authorizations, payment_reconciliation, payments, question_governance, questions, sessions, supervision, users

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
app.include_router(entries.router, prefix=settings.api_v1_prefix)
app.include_router(center_incidents.router, prefix=settings.api_v1_prefix)
app.include_router(center_stations.router, prefix=settings.api_v1_prefix)
app.include_router(device_sessions.router, prefix=settings.api_v1_prefix)
app.include_router(exam_monitoring.router, prefix=settings.api_v1_prefix)
app.include_router(exam_reviews.router, prefix=settings.api_v1_prefix)
app.include_router(exam_question_traces.router, prefix=settings.api_v1_prefix)
app.include_router(candidate_submissions.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(supervision.router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)

"""P11 SOC telemetry — traces OTLP best-effort + événements HTTP sanitised.

Aucun exporter n'est autorisé à bloquer le trafic candidat. Les attributs sont
limités aux routes templates, statuts, méthodes, request_id et références HMAC.
"""
from __future__ import annotations

import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.soc_config import get_soc_settings
from app.soc_metrics import record_security_event
from app.soc_privacy import pseudonymize_ip

log = logging.getLogger("coderoute.soc")
_TRACER = None


def _route_template(request) -> str:
    route = request.scope.get("route")
    value = getattr(route, "path", None)
    if not isinstance(value, str) or not value:
        return "unmatched"
    return value[:160]


def _client_ref(request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    raw = forwarded or (request.client.host if request.client else "unknown")
    return pseudonymize_ip(raw)


def _parse_headers(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for chunk in raw.split(","):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        if key.strip() and value.strip():
            result[key.strip()] = value.strip()
    return result


def _trace_endpoint(base: str) -> str:
    value = base.rstrip("/")
    return value if value.endswith("/v1/traces") else f"{value}/v1/traces"


def init_soc_telemetry() -> bool:
    """Initialise un tracer OTLP. Une panne exporter ne bloque jamais l'API."""
    global _TRACER
    settings = get_soc_settings()
    if not settings.enabled or not settings.otel_traces_enabled:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

        resource = Resource.create(
            {
                "service.name": settings.otel_service_name,
                "service.version": os.getenv("APP_VERSION", "0.14.0"),
                "deployment.environment.name": os.getenv("ENVIRONMENT", "development"),
            }
        )
        provider = TracerProvider(
            resource=resource,
            sampler=ParentBased(TraceIdRatioBased(settings.otel_sample_ratio)),
        )
        exporter = OTLPSpanExporter(
            endpoint=_trace_endpoint(settings.otel_endpoint),
            headers=_parse_headers(settings.otel_headers),
            timeout=5.0,
        )
        provider.add_span_processor(
            BatchSpanProcessor(exporter, max_queue_size=2048, max_export_batch_size=256)
        )
        trace.set_tracer_provider(provider)
        _TRACER = trace.get_tracer("coderoute.soc", "1.0")
        log.info("soc_otel_enabled", extra={"otel_service": settings.otel_service_name})
        return True
    except Exception as exc:
        _TRACER = None
        log.warning("soc_otel_init_failed", extra={"error_type": exc.__class__.__name__})
        return False


def _current_tracer():
    if _TRACER is not None:
        return _TRACER
    try:
        from opentelemetry import trace
        return trace.get_tracer("coderoute.soc", "1.0")
    except Exception:
        return None


class SOCRequestMiddleware(BaseHTTPMiddleware):
    """Trace/log HTTP avec route template et références pseudonymisées seulement."""

    async def dispatch(self, request, call_next):
        settings = get_soc_settings()
        if not settings.enabled:
            return await call_next(request)

        path = request.url.path
        if path in {"/health", "/health/live", "/health/readiness", "/internal/metrics"} or path.startswith("/static"):
            return await call_next(request)

        request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id", "")[:128]
        client_ref = _client_ref(request)
        method = request.method.upper()[:12]
        started = time.perf_counter()
        status_code = 500
        tracer = _current_tracer()
        span_cm = tracer.start_as_current_span(f"HTTP {method}") if tracer is not None else None

        def _finish_log(route: str, elapsed_ms: float) -> None:
            event = "http.request"
            metric_kind: str | None = None
            level = logging.INFO
            if status_code in {401, 403}:
                event, metric_kind, level = "security.access_denied", "access_denied", logging.WARNING
            elif status_code == 429:
                event, metric_kind, level = "security.rate_limited", "rate_limited", logging.WARNING
            elif status_code >= 500:
                event, metric_kind, level = "security.server_error", "server_error", logging.ERROR
            if metric_kind:
                record_security_event(metric_kind)
            log.log(
                level,
                event,
                extra={
                    "request_id": request_id or None,
                    "method": method,
                    "route": route,
                    "status": status_code,
                    "duration_ms": round(elapsed_ms, 1),
                    "client_ref": client_ref,
                    "security_event": metric_kind is not None,
                },
            )

        if span_cm is None:
            try:
                response = await call_next(request)
                status_code = int(response.status_code)
                return response
            finally:
                _finish_log(_route_template(request), (time.perf_counter() - started) * 1000)

        with span_cm as span:
            try:
                response = await call_next(request)
                status_code = int(response.status_code)
                return response
            except Exception as exc:
                try:
                    span.record_exception(exc)
                except Exception:
                    pass
                raise
            finally:
                route = _route_template(request)
                elapsed_ms = (time.perf_counter() - started) * 1000
                try:
                    span.update_name(f"HTTP {method} {route}")
                    span.set_attribute("http.request.method", method)
                    span.set_attribute("http.route", route)
                    span.set_attribute("http.response.status_code", status_code)
                    if request_id:
                        span.set_attribute("coderoute.request_id", request_id)
                    span.set_attribute("coderoute.client_ref", client_ref)
                except Exception:
                    pass
                _finish_log(route, elapsed_ms)

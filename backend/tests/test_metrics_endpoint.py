from types import SimpleNamespace

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.reliability_metrics import _route_template
from app.routers import metrics as metrics_router


class MetricsSettings:
    metrics_enabled = True
    metrics_token = "metrics-token-" + ("m" * 40)


def _scope(route_path: str):
    return {
        "type": "http",
        "method": "GET",
        "path": "/ignored/raw/123456789",
        "headers": [],
        "route": SimpleNamespace(path=route_path),
    }


def test_route_metric_uses_template_not_raw_identifier() -> None:
    request = Request(_scope("/api/v1/exams/{attempt_id}/status"))
    route = _route_template(request)
    assert route == "/api/v1/exams/{attempt_id}/status"
    assert "123456789" not in route


def test_metrics_disabled_is_hidden(monkeypatch) -> None:
    monkeypatch.setattr(
        metrics_router,
        "get_reliability_settings",
        lambda: SimpleNamespace(metrics_enabled=False, metrics_token=""),
    )
    with TestClient(app) as client:
        response = client.get("/internal/metrics")
    assert response.status_code == 404


def test_metrics_requires_machine_token(monkeypatch) -> None:
    monkeypatch.setattr(metrics_router, "get_reliability_settings", lambda: MetricsSettings())
    with TestClient(app) as client:
        missing = client.get("/internal/metrics")
        wrong = client.get("/internal/metrics", headers={"Authorization": "Bearer wrong"})
    assert missing.status_code == 401
    assert wrong.status_code == 401


def test_metrics_scrape_is_no_store_and_prometheus_formatted(monkeypatch) -> None:
    monkeypatch.setattr(metrics_router, "get_reliability_settings", lambda: MetricsSettings())
    with TestClient(app) as client:
        client.get("/health/live")
        response = client.get(
            "/internal/metrics",
            headers={"Authorization": f"Bearer {MetricsSettings.metrics_token}"},
        )
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert response.headers["cache-control"] == "no-store"
    assert "coderoute_http_requests_total" in response.text
    assert "coderoute_http_request_duration_seconds" in response.text

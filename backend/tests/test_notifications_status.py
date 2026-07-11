"""Test — statut et test des canaux de notification."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import init_db
from tests.conftest import get_admin_headers


def test_notifications_status_lists_channels() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/ops/notifications-status",
                       headers=get_admin_headers(client))
        assert r.status_code == 200
        data = r.json()
        assert set(data["channels"]) == {"email", "sms", "whatsapp"}
        assert "active_channels" in data
        assert "any_active" in data
        # Sans clés configurées, aucun canal actif
        for ch in data["channels"].values():
            assert "configured" in ch
            assert "provider" in ch
            assert "env_keys" in ch


def test_notifications_test_dev_mode() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.post("/api/v1/admin/ops/notifications-test",
                        json={"channel": "email", "to": "test@dntt.gov.gn"},
                        headers=get_admin_headers(client))
        assert r.status_code == 200
        # En dev (pas de clé), le fallback console renvoie ok=True
        assert r.json()["ok"] is True


def test_notifications_test_rejects_bad_params() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.post("/api/v1/admin/ops/notifications-test",
                        json={"channel": "invalid", "to": ""},
                        headers=get_admin_headers(client))
        assert r.status_code == 200
        assert r.json()["ok"] is False

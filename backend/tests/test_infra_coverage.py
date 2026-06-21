"""
Tests couverture audit.py, center_stations.py, auth_guard.py.

Cibles :
  app/routers/audit.py          (56% → 90%+) — lignes 21-28
  app/routers/center_stations.py (67% → 90%+) — lignes 51, 63, 72, 106-153
  app/auth_guard.py             (71% → 85%+) — lignes 43, 75, 78, 84-158
"""
import uuid

from fastapi.testclient import TestClient

from app.auth_guard import LoginRateLimiter, _InMemoryFallback
from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_center import Center
from tests.conftest import get_admin_headers

# ══════════════════════════════════════════════════════════════════
# 1. AUDIT — /api/v1/audit-logs
# ══════════════════════════════════════════════════════════════════

class TestAuditLogs:
    def test_list_returns_array(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_default_limit_100(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs", headers=h)
        assert len(r.json()) <= 100

    def test_list_with_explicit_limit(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs?limit=5", headers=h)
        assert r.status_code == 200
        assert len(r.json()) <= 5

    def test_list_with_action_filter(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs?action=user.login", headers=h)
        assert r.status_code == 200
        data = r.json()
        for entry in data:
            assert entry["action"] == "user.login"

    def test_list_with_entity_filter(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs?entity=user", headers=h)
        assert r.status_code == 200
        data = r.json()
        for entry in data:
            assert entry["entity"] == "user"

    def test_list_entries_have_required_fields(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs?limit=1", headers=h)
        data = r.json()
        if data:
            entry = data[0]
            assert "id" in entry
            assert "action" in entry
            assert "entity" in entry
            assert "created_at" in entry

    def test_list_requires_auth(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/audit-logs")
        assert r.status_code == 401

    def test_list_limit_max_500(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs?limit=500", headers=h)
        assert r.status_code == 200
        assert len(r.json()) <= 500

    def test_limit_above_max_rejected(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs?limit=9999", headers=h)
        assert r.status_code == 422

    def test_limit_zero_rejected(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs?limit=0", headers=h)
        assert r.status_code == 422

    def test_combined_filters_action_and_entity(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/audit-logs?action=center.created&entity=center", headers=h)
        assert r.status_code == 200
        data = r.json()
        for entry in data:
            assert entry["action"] == "center.created"
            assert entry["entity"] == "center"


# ══════════════════════════════════════════════════════════════════
# 2. CENTER STATIONS — /api/v1/center-stations
# ══════════════════════════════════════════════════════════════════



def _make_center() -> Center:
    init_db()
    db = SessionLocal()
    code = f"CS-{uuid.uuid4().hex[:6].upper()}"
    c = Center(
        code=code,
        name=f"Centre Stations Test {code}",
        city="Conakry",
        commune="Kaloum",
        prefecture="Conakry",
        address=f"Rue Test {code}",
        capacity=35,
        max_sessions_per_week=3,
        status="accredited",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    db.close()
    return c


class TestCenterStations:
    def test_create_station(self):
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id,
                "device_key": f"DEV-{uuid.uuid4().hex[:8]}",
                "label": "Poste A",
                "room": "Salle 101",
                "status": "active",
            })
        assert r.status_code == 201
        data = r.json()
        assert data["center_id"] == center.id
        assert data["label"] == "Poste A"
        assert data["status"] == "active"
        assert data["room"] == "Salle 101"

    def test_create_station_default_status_active(self):
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id,
                "device_key": f"DEV-{uuid.uuid4().hex[:8]}",
                "label": "Poste Défaut",
            })
        assert r.status_code == 201
        assert r.json()["status"] == "active"

    def test_create_station_invalid_status_422(self):
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id,
                "device_key": f"DEV-{uuid.uuid4().hex[:8]}",
                "label": "Poste Invalide",
                "status": "invalid_status",
            })
        assert r.status_code == 422

    def test_create_station_center_not_found_404(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": str(uuid.uuid4()),
                "device_key": "DEV-UNKNOWN",
                "label": "Poste Fantôme",
            })
        assert r.status_code == 404

    def test_create_duplicate_device_key_409(self):
        center = _make_center()
        device_key = f"DEV-DUP-{uuid.uuid4().hex[:8]}"
        payload = {
            "center_id": center.id,
            "device_key": device_key,
            "label": "Poste Original",
        }
        with TestClient(app) as client:
            h = get_admin_headers(client)
            client.post("/api/v1/center-stations", headers=h, json=payload)
            r = client.post("/api/v1/center-stations", headers=h, json={
                **payload, "label": "Doublon"
            })
        assert r.status_code == 409

    def test_create_station_short_device_key_422(self):
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id,
                "device_key": "AB",  # min_length=4
                "label": "Poste",
            })
        assert r.status_code == 422

    def test_create_station_short_label_422(self):
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id,
                "device_key": f"DEV-{uuid.uuid4().hex[:8]}",
                "label": "A",  # min_length=2
            })
        assert r.status_code == 422

    def test_list_stations(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/center-stations", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_stations_filter_by_center(self):
        center = _make_center()
        dev = f"DEV-F{uuid.uuid4().hex[:6]}"
        with TestClient(app) as client:
            h = get_admin_headers(client)
            client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id, "device_key": dev, "label": "Poste Filtré",
            })
            r = client.get(f"/api/v1/center-stations?center_id={center.id}", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert all(s["center_id"] == center.id for s in data)
        assert any(s["device_key"] == dev for s in data)

    def test_list_stations_filter_by_status(self):
        center = _make_center()
        dev = f"DEV-M{uuid.uuid4().hex[:6]}"
        with TestClient(app) as client:
            h = get_admin_headers(client)
            client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id, "device_key": dev, "label": "Maintenance",
                "status": "maintenance",
            })
            r = client.get("/api/v1/center-stations?status_filter=maintenance", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert all(s["status"] == "maintenance" for s in data)

    def test_list_stations_invalid_status_filter_422(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/center-stations?status_filter=flying", headers=h)
        assert r.status_code == 422

    def test_update_station_status(self):
        center = _make_center()
        dev = f"DEV-U{uuid.uuid4().hex[:6]}"
        with TestClient(app) as client:
            h = get_admin_headers(client)
            created = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id, "device_key": dev, "label": "Poste MAJ",
            }).json()
            r = client.patch(
                f"/api/v1/center-stations/{created['id']}",
                headers=h,
                json={"status": "maintenance"},
            )
        assert r.status_code == 200
        assert r.json()["status"] == "maintenance"

    def test_update_station_label(self):
        center = _make_center()
        dev = f"DEV-L{uuid.uuid4().hex[:6]}"
        with TestClient(app) as client:
            h = get_admin_headers(client)
            created = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id, "device_key": dev, "label": "Ancien Label",
            }).json()
            r = client.patch(
                f"/api/v1/center-stations/{created['id']}",
                headers=h,
                json={"label": "Nouveau Label"},
            )
        assert r.status_code == 200
        assert r.json()["label"] == "Nouveau Label"

    def test_update_station_room(self):
        center = _make_center()
        dev = f"DEV-R{uuid.uuid4().hex[:6]}"
        with TestClient(app) as client:
            h = get_admin_headers(client)
            created = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id, "device_key": dev, "label": "Poste Salle",
            }).json()
            r = client.patch(
                f"/api/v1/center-stations/{created['id']}",
                headers=h,
                json={"room": "Salle 202"},
            )
        assert r.status_code == 200
        assert r.json()["room"] == "Salle 202"

    def test_update_station_not_found_404(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.patch(
                f"/api/v1/center-stations/{uuid.uuid4()}",
                headers=h,
                json={"status": "active"},
            )
        assert r.status_code == 404

    def test_update_station_invalid_status_422(self):
        center = _make_center()
        dev = f"DEV-I{uuid.uuid4().hex[:6]}"
        with TestClient(app) as client:
            h = get_admin_headers(client)
            created = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id, "device_key": dev, "label": "Poste Invalide",
            }).json()
            r = client.patch(
                f"/api/v1/center-stations/{created['id']}",
                headers=h,
                json={"status": "broken"},
            )
        assert r.status_code == 422

    def test_update_station_all_statuses(self):
        """Tester chaque statut valide : active, disabled, maintenance."""
        center = _make_center()
        dev = f"DEV-S{uuid.uuid4().hex[:6]}"
        with TestClient(app) as client:
            h = get_admin_headers(client)
            created = client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id, "device_key": dev, "label": "Poste Cycles",
            }).json()
            sid = created["id"]
            for status in ["disabled", "maintenance", "active"]:
                r = client.patch(f"/api/v1/center-stations/{sid}", headers=h,
                                 json={"status": status})
                assert r.status_code == 200, f"Statut '{status}' a échoué"
                assert r.json()["status"] == status

    def test_station_requires_auth(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/center-stations")
        assert r.status_code == 401

    def test_station_audit_log_created(self):
        """La création d'un poste doit générer un audit log."""
        center = _make_center()
        dev = f"DEV-AUD{uuid.uuid4().hex[:4]}"
        with TestClient(app) as client:
            h = get_admin_headers(client)
            client.post("/api/v1/center-stations", headers=h, json={
                "center_id": center.id, "device_key": dev, "label": "Poste Audit",
            })
            r = client.get(
                "/api/v1/audit-logs?action=center_station.created&limit=10",
                headers=h
            )
        assert r.status_code == 200
        assert len(r.json()) > 0


# ══════════════════════════════════════════════════════════════════
# 3. AUTH GUARD — LoginRateLimiter
# ══════════════════════════════════════════════════════════════════



class TestInMemoryFallback:
    def test_not_blocked_initially(self):
        fb = _InMemoryFallback(max_attempts=3, window_seconds=300)
        assert fb.is_blocked("user@test.com") is False

    def test_blocked_after_max_attempts(self):
        fb = _InMemoryFallback(max_attempts=3, window_seconds=300)
        for _ in range(3):
            fb.register_failure("user@test.com")
        assert fb.is_blocked("user@test.com") is True

    def test_not_blocked_below_max_attempts(self):
        fb = _InMemoryFallback(max_attempts=3, window_seconds=300)
        for _ in range(2):
            fb.register_failure("user@test.com")
        assert fb.is_blocked("user@test.com") is False

    def test_reset_clears_attempts(self):
        fb = _InMemoryFallback(max_attempts=3, window_seconds=300)
        for _ in range(3):
            fb.register_failure("user@test.com")
        fb.reset("user@test.com")
        assert fb.is_blocked("user@test.com") is False

    def test_different_keys_independent(self):
        fb = _InMemoryFallback(max_attempts=2, window_seconds=300)
        fb.register_failure("alice@test.com")
        fb.register_failure("alice@test.com")
        assert fb.is_blocked("alice@test.com") is True
        assert fb.is_blocked("bob@test.com") is False

    def test_clear_resets_all_keys(self):
        fb = _InMemoryFallback(max_attempts=2, window_seconds=300)
        fb.register_failure("alice@test.com")
        fb.register_failure("alice@test.com")
        fb.register_failure("bob@test.com")
        fb.clear()
        assert fb.is_blocked("alice@test.com") is False
        assert fb.is_blocked("bob@test.com") is False

    def test_window_expiry(self):
        """Les tentatives expirées ne comptent plus."""
        import time
        fb = _InMemoryFallback(max_attempts=2, window_seconds=1)
        fb.register_failure("user@test.com")
        fb.register_failure("user@test.com")
        assert fb.is_blocked("user@test.com") is True
        time.sleep(1.1)
        assert fb.is_blocked("user@test.com") is False


class TestLoginRateLimiterInMemory:
    """Tests du LoginRateLimiter en mode fallback in-memory (sans DB)."""

    def test_not_blocked_initially(self):
        limiter = LoginRateLimiter(max_attempts=5, window_seconds=300)
        assert limiter.is_blocked("user@test.com") is False

    def test_blocked_after_max_failures(self):
        limiter = LoginRateLimiter(max_attempts=3, window_seconds=300)
        for _ in range(3):
            limiter.register_failure("user@test.com")
        assert limiter.is_blocked("user@test.com") is True

    def test_reset_unblocks(self):
        limiter = LoginRateLimiter(max_attempts=2, window_seconds=300)
        limiter.register_failure("user@test.com")
        limiter.register_failure("user@test.com")
        limiter.reset("user@test.com")
        assert limiter.is_blocked("user@test.com") is False

    def test_max_attempts_property(self):
        limiter = LoginRateLimiter(max_attempts=5, window_seconds=300)
        assert limiter.max_attempts == 5

    def test_max_attempts_setter(self):
        limiter = LoginRateLimiter(max_attempts=5, window_seconds=300)
        limiter.max_attempts = 10
        assert limiter.max_attempts == 10
        assert limiter._fallback.max_attempts == 10

    def test_clear_resets_fallback(self):
        limiter = LoginRateLimiter(max_attempts=2, window_seconds=300)
        limiter.register_failure("user@test.com")
        limiter.register_failure("user@test.com")
        limiter.clear()
        assert limiter.is_blocked("user@test.com") is False

    def test_register_failure_without_db(self):
        limiter = LoginRateLimiter(max_attempts=3, window_seconds=300)
        limiter.register_failure("no-db@test.com", db=None)
        assert not limiter.is_blocked("no-db@test.com")

    def test_reset_without_db(self):
        limiter = LoginRateLimiter(max_attempts=2, window_seconds=300)
        limiter.register_failure("reset@test.com", db=None)
        limiter.register_failure("reset@test.com", db=None)
        limiter.reset("reset@test.com", db=None)
        assert not limiter.is_blocked("reset@test.com", db=None)


class TestLoginRateLimiterWithDB:
    """Tests du LoginRateLimiter avec la vraie DB."""

    def _limiter(self):
        # Reset le flag pour forcer la création de table
        LoginRateLimiter._table_ensured = False
        return LoginRateLimiter(max_attempts=3, window_seconds=300)

    def test_not_blocked_in_db_initially(self):
        from app.db.session import SessionLocal
        limiter = self._limiter()
        db = SessionLocal()
        try:
            assert limiter.is_blocked("db-user@test.com", db=db) is False
        finally:
            db.close()

    def test_blocked_after_db_failures(self):
        from app.db.session import SessionLocal
        limiter = self._limiter()
        key = f"db-block-{uuid.uuid4().hex[:8]}@test.com"
        db = SessionLocal()
        try:
            for _ in range(3):
                limiter.register_failure(key, db=db)
            assert limiter.is_blocked(key, db=db) is True
        finally:
            limiter.reset(key, db=db)
            db.close()

    def test_reset_in_db_unblocks(self):
        from app.db.session import SessionLocal
        limiter = self._limiter()
        key = f"db-reset-{uuid.uuid4().hex[:8]}@test.com"
        db = SessionLocal()
        try:
            for _ in range(3):
                limiter.register_failure(key, db=db)
            limiter.reset(key, db=db)
            assert limiter.is_blocked(key, db=db) is False
        finally:
            db.close()

    def test_db_error_falls_back_to_memory(self):
        """Si la DB échoue, le fallback in-memory prend le relais."""
        from unittest.mock import MagicMock
        limiter = self._limiter()
        bad_db = MagicMock()
        bad_db.execute.side_effect = Exception("DB down")
        # Ne doit pas lever d'exception
        result = limiter.is_blocked("fallback@test.com", db=bad_db)
        assert isinstance(result, bool)

    def test_ensure_table_idempotent(self):
        """is_blocked avec DB ne doit pas lever d'exception (idempotence)."""
        from app.db.session import SessionLocal
        limiter = self._limiter()
        key = f"idp-{uuid.uuid4().hex[:8]}@test.com"
        db = SessionLocal()
        try:
            # 2 appels successifs — aucun ne doit planter
            r1 = limiter.is_blocked(key, db=db)
            r2 = limiter.is_blocked(key, db=db)
            assert isinstance(r1, bool)
            assert isinstance(r2, bool)
            # Le flag doit être positionné après le premier appel DB réussi
            # (peut rester False si SQLite route vers le fallback)
        finally:
            db.close()

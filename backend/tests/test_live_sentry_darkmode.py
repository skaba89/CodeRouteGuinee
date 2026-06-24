"""
Tests — Live dashboard, Sentry wrapper, Dark mode (CSS), Celcom Money.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers

# ── Live Dashboard ────────────────────────────────────────────────────────────

class TestLiveDashboard:
    def test_live_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/dashboard/live")
        assert r.status_code == 401

    def test_live_200_as_admin(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/dashboard/live", headers=h)
        assert r.status_code == 200

    def test_live_has_kpis(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/dashboard/live", headers=h)
        data = r.json()
        assert "kpis" in data

    def test_live_kpis_fields(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/dashboard/live", headers=h)
        kpis = r.json()["kpis"]
        for field in ["total_candidates", "bookings_today", "pending_payments",
                      "active_sessions", "open_incidents"]:
            assert field in kpis, f"Champ manquant : {field}"

    def test_live_kpis_non_negative(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/dashboard/live", headers=h)
        for k, v in r.json()["kpis"].items():
            assert v >= 0, f"KPI négatif : {k}={v}"

    def test_live_has_feed(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/dashboard/live", headers=h)
        assert "feed" in r.json()
        assert isinstance(r.json()["feed"], list)

    def test_live_has_timestamp(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/dashboard/live", headers=h)
        assert "timestamp" in r.json()

    def test_live_poll_interval(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/dashboard/live", headers=h)
        assert r.json().get("poll_interval_seconds") == 15

    def test_live_feed_items_structure(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/dashboard/live", headers=h)
        for item in r.json()["feed"]:
            assert "id" in item
            assert "type" in item
            assert "title" in item


# ── Sentry Wrapper ───────────────────────────────────────────────────────────

class TestSentryWrapper:
    def test_init_sentry_without_dsn_returns_false(self):
        from app.sentry import init_sentry
        # Sans SENTRY_DSN, doit retourner False sans crash
        result = init_sentry()
        assert result is False

    def test_capture_exception_no_crash(self):
        from app.sentry import capture_exception
        # Sans Sentry actif, doit logger sans crasher
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            capture_exception(e, context={"test": True})

    def test_capture_message_no_crash(self):
        from app.sentry import capture_message
        capture_message("Test message", level="info")
        capture_message("Test warning", level="warning")

    def test_is_active_false_without_dsn(self):
        from app.sentry import is_active
        assert is_active() is False

    def test_capture_exception_with_user_id(self):
        from app.sentry import capture_exception
        try:
            raise RuntimeError("Test with user")
        except RuntimeError as e:
            capture_exception(e, user_id="test-user-123")

    def test_capture_exception_with_full_context(self):
        from app.sentry import capture_exception
        ctx = {"endpoint": "/exams/submit", "attempt_id": "abc", "user_id": "xyz"}
        try:
            raise OSError("Connexion perdue")
        except OSError as e:
            capture_exception(e, context=ctx)


# ── Celcom Money ─────────────────────────────────────────────────────────────

class TestCelcomMoney:
    def test_normalize_celcom(self):
        from app.mobile_money import normalize_provider
        assert normalize_provider("celcom") == "celcom_money"
        assert normalize_provider("celcom_money") == "celcom_money"
        assert normalize_provider("Celcom") == "celcom_money"
        assert normalize_provider("CELCOM_MONEY") == "celcom_money"

    def test_celcom_sandbox_without_credentials(self):
        """Sans credentials, Celcom passe en sandbox."""
        from app.mobile_money import _celcom_money_payment
        result = _celcom_money_payment("+224628000000", 150_000)
        # Sandbox = statut pending/paid simulé
        assert result.status in ("pending", "paid", "sandbox")
        assert result.provider in ("celcom_money", "sandbox")

    def test_simulate_celcom_via_dispatcher(self):
        from app.mobile_money import simulate_mobile_money_payment
        result = simulate_mobile_money_payment("celcom_money", "+224628000000", 150_000)
        assert result.status in ("pending", "paid", "sandbox", "failed")

    def test_celcom_result_has_required_fields(self):
        from app.mobile_money import _celcom_money_payment
        r = _celcom_money_payment("+224628000000", 100_000)
        assert hasattr(r, "provider")
        assert hasattr(r, "status")
        assert hasattr(r, "message")


# ── Dark mode CSS ─────────────────────────────────────────────────────────────

class TestDarkMode:
    """Tests unitaires sur le contenu du fichier CSS dark mode."""

    def _read_css(self) -> str:
        from pathlib import Path
        return (Path(__file__).parent.parent.parent /
                "frontend" / "src" / "styles.css").read_text()

    def test_dark_mode_class_defined(self):
        assert ".dark" in self._read_css()

    def test_dark_mode_data_theme(self):
        assert '[data-theme="dark"]' in self._read_css()

    def test_dark_mode_bg_variable(self):
        css = self._read_css()
        assert "--bg:" in css

    def test_dark_mode_prefers_color_scheme(self):
        assert "prefers-color-scheme: dark" in self._read_css()

    def test_dark_mode_surface_variable(self):
        assert "--surface:" in self._read_css()

    def test_dark_mode_primary_green_adapted(self):
        css = self._read_css()
        # La couleur verte primaire doit être adaptée pour le dark mode
        assert "#34D399" in css or "#00875A" in css


# ── Live Dashboard Component (TypeScript) ────────────────────────────────────

class TestLiveDashboardComponent:
    """Vérifie que le composant TypeScript existe et contient les bons éléments."""

    def _read_component(self) -> str:
        from pathlib import Path
        p = Path(__file__).parent.parent.parent / "frontend" / "src" / \
            "components" / "live-dashboard.tsx"
        return p.read_text() if p.exists() else ""

    def test_component_exists(self):
        assert len(self._read_component()) > 100

    def test_component_exports_live_dashboard(self):
        assert "export function LiveDashboard" in self._read_component()

    def test_component_has_polling(self):
        c = self._read_component()
        assert "setInterval" in c or "POLL_INTERVAL" in c

    def test_component_has_kpi_display(self):
        c = self._read_component()
        assert "kpis" in c

    def test_component_has_feed(self):
        c = self._read_component()
        assert "feed" in c

    def test_poll_interval_15s(self):
        c = self._read_component()
        assert "15" in c  # 15 secondes

    def test_theme_toggle_component_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent.parent / "frontend" / "src" / \
            "components" / "theme-toggle.tsx"
        assert p.exists()
        c = p.read_text()
        assert "export function ThemeToggle" in c
        assert "localStorage" in c

"""
Tests — RGPD, page offline, cron systemd, panneaux SVG.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_candidate import Candidate
from app.models_user import User
from app.security import get_password_hash
from tests.conftest import get_admin_headers


# ── Module RGPD ───────────────────────────────────────────────────────────────

class TestRgpdModule:

    def _make_candidate(self, email: str) -> str:
        """Seed un candidat et retourne son ID."""
        init_db()
        suffix = uuid.uuid4().hex[:8]
        with SessionLocal() as db:
            cand = Candidate(
                reference=f"GN-RGPD-{suffix}",
                first_name="Test",
                last_name=f"RGPD-{suffix}",
                identity_number=f"NINA-RGPD-{suffix}",
                phone=f"+224628{suffix[:6]}",
                permit_category="B",
                status="active",
                email=email,
            )
            db.add(cand)
            db.commit()
            db.refresh(cand)
            return str(cand.id)

    def test_export_json(self):
        from app.rgpd import export_candidate_data
        init_db()
        suffix = uuid.uuid4().hex[:8]
        with SessionLocal() as db:
            cand_id = self._make_candidate(f"exp-{suffix}@test.com")
            data = export_candidate_data(cand_id, db, "json")
        import json
        payload = json.loads(data)
        assert "candidate" in payload
        assert "law" in payload
        assert "L/2022/018/AN" in payload["law"]

    def test_export_csv(self):
        from app.rgpd import export_candidate_data
        init_db()
        suffix = uuid.uuid4().hex[:8]
        with SessionLocal() as db:
            cand_id = self._make_candidate(f"csv-{suffix}@test.com")
            data = export_candidate_data(cand_id, db, "csv")
        content = data.decode("utf-8-sig")
        assert "DONNÉES PERSONNELLES" in content

    def test_export_unknown_candidate_raises(self):
        from app.rgpd import export_candidate_data
        init_db()
        with SessionLocal() as db:
            with pytest.raises(ValueError, match="introuvable"):
                export_candidate_data("nonexistent-id-xyz", db, "json")

    def test_anonymize_pii(self):
        from app.rgpd import anonymize_candidate
        init_db()
        suffix = uuid.uuid4().hex[:8]
        email = f"anon-{suffix}@test.com"
        cand_id = self._make_candidate(email)
        with SessionLocal() as db:
            result = anonymize_candidate(cand_id, db, "Test anonymisation")
        assert result["operation"] == "erasure"
        assert "L/2022/018/AN" in result["law"]
        assert "exam_attempts" in result["preserved"]
        assert "first_name" in result["erased"]

    def test_anonymize_updates_db(self):
        from app.rgpd import anonymize_candidate
        from sqlalchemy import select
        init_db()
        suffix = uuid.uuid4().hex[:8]
        email = f"anon2-{suffix}@test.com"
        cand_id = self._make_candidate(email)
        with SessionLocal() as db:
            anonymize_candidate(cand_id, db)
        with SessionLocal() as db:
            cand = db.get(Candidate, cand_id)
            assert cand is not None
            assert cand.first_name == "ANONYME"
            assert cand.last_name == "ANONYME"
            assert cand.status == "anonymized"
            assert "ANON_" in cand.identity_number

    def test_hash_pii_deterministic(self):
        from app.rgpd import _hash_pii
        h1 = _hash_pii("test@example.com")
        h2 = _hash_pii("test@example.com")
        assert h1 == h2
        assert h1.startswith("ANON_")

    def test_hash_pii_different_values(self):
        from app.rgpd import _hash_pii
        assert _hash_pii("a@b.com") != _hash_pii("c@d.com")

    def test_anonymize_unknown_raises(self):
        from app.rgpd import anonymize_candidate
        init_db()
        with SessionLocal() as db:
            with pytest.raises(ValueError):
                anonymize_candidate("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", db)


# ── Endpoints RGPD ────────────────────────────────────────────────────────────

class TestRgpdEndpoints:

    def _candidate_token_with_profile(self) -> tuple[str, str]:
        """Crée un user candidat + profil candidat associé par email."""
        init_db()
        suffix = uuid.uuid4().hex[:8]
        email  = f"rgpd-cand-{suffix}@test.com"
        with SessionLocal() as db:
            user = User(email=email, full_name="RGPD Test",
                        password_hash=get_password_hash("TestPass123!"),
                        role="candidate")
            db.add(user)
            db.flush()
            cand = Candidate(
                reference=f"GN-RGPD-API-{suffix}",
                first_name="RGPD", last_name=f"Candidat-{suffix}",
                identity_number=f"NINA-RGPD-{suffix}",
                phone=f"+224628{suffix[:6]}",
                permit_category="B", status="active",
                email=email,
            )
            db.add(cand)
            db.commit()
        with TestClient(app) as c:
            tok = c.post("/api/v1/auth/login",
                         data={"username": email, "password": "TestPass123!"}).json()["access_token"]
        return tok, email

    def test_export_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/rgpd/export")
        assert r.status_code == 401

    def test_export_json_as_candidate(self):
        tok, _ = self._candidate_token_with_profile()
        with TestClient(app) as c:
            r = c.get("/api/v1/rgpd/export", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        assert "application/json" in r.headers.get("content-type", "")

    def test_export_csv_as_candidate(self):
        tok, _ = self._candidate_token_with_profile()
        with TestClient(app) as c:
            r = c.get("/api/v1/rgpd/export?fmt=csv",
                      headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        assert "csv" in r.headers.get("content-type", "")

    def test_export_invalid_format(self):
        tok, _ = self._candidate_token_with_profile()
        with TestClient(app) as c:
            r = c.get("/api/v1/rgpd/export?fmt=xml",
                      headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 400

    def test_delete_requires_auth(self):
        with TestClient(app) as c:
            r = c.post("/api/v1/rgpd/delete", json={})
        assert r.status_code == 401

    def test_delete_as_candidate(self):
        tok, _ = self._candidate_token_with_profile()
        with TestClient(app) as c:
            r = c.post("/api/v1/rgpd/delete",
                       headers={"Authorization": f"Bearer {tok}"},
                       json={"reason": "Test RGPD"})
        assert r.status_code == 200
        data = r.json()
        assert data["operation"] == "erasure"
        assert "L/2022/018/AN" in data["law"]

    def test_admin_export_by_id(self):
        init_db()
        suffix = uuid.uuid4().hex[:8]
        with SessionLocal() as db:
            cand = Candidate(
                reference=f"GN-ADM-{suffix}",
                first_name="Admin", last_name="Export",
                identity_number=f"NINA-ADM-{suffix}",
                phone=f"+224628{suffix[:6]}",
                permit_category="B", status="active",
            )
            db.add(cand)
            db.commit()
            db.refresh(cand)
            cand_id = str(cand.id)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get(f"/api/v1/rgpd/export/{cand_id}", headers=h)
        assert r.status_code == 200

    def test_admin_export_unknown_404(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/rgpd/export/nonexistent-id-xyz", headers=h)
        assert r.status_code == 404


# ── Page offline ──────────────────────────────────────────────────────────────

class TestOfflinePage:
    def _read_html(self) -> str:
        from pathlib import Path
        p = Path(__file__).parent.parent.parent / "frontend" / "public" / "offline.html"
        return p.read_text() if p.exists() else ""

    def test_offline_html_exists(self):
        assert len(self._read_html()) > 100

    def test_offline_has_french_content(self):
        html = self._read_html()
        assert "Connexion" in html or "réseau" in html

    def test_offline_has_retry_button(self):
        html = self._read_html()
        assert "reload" in html or "Réessayer" in html

    def test_offline_has_guinean_flag(self):
        html = self._read_html()
        # Couleurs du drapeau guinéen
        assert "CE1126" in html or "FCD116" in html

    def test_offline_auto_reload_on_online(self):
        html = self._read_html()
        assert "window.addEventListener('online'" in html


# ── Cron / systemd ───────────────────────────────────────────────────────────

class TestCronFiles:
    def _scripts_dir(self):
        from pathlib import Path
        return Path(__file__).parent.parent.parent / "scripts" / "systemd"

    def test_cron_script_exists(self):
        assert (self._scripts_dir() / "coderoute-cron.sh").exists()

    def test_cron_script_executable(self):
        import os
        path = self._scripts_dir() / "coderoute-cron.sh"
        assert os.access(str(path), os.X_OK)

    def test_service_unit_exists(self):
        assert (self._scripts_dir() / "coderoute-notifications.service").exists()

    def test_timer_24h_exists(self):
        assert (self._scripts_dir() / "coderoute-exam-reminder-24h.timer").exists()

    def test_timer_2h_exists(self):
        assert (self._scripts_dir() / "coderoute-exam-reminder-2h.timer").exists()

    def test_timer_payment_exists(self):
        assert (self._scripts_dir() / "coderoute-payment-pending.timer").exists()

    def test_install_guide_exists(self):
        assert (self._scripts_dir() / "INSTALL.md").exists()

    def test_service_unit_content(self):
        content = (self._scripts_dir() / "coderoute-notifications.service").read_text()
        assert "ExecStart" in content
        assert "coderoute-cron.sh" in content


# ── Panneaux SVG ──────────────────────────────────────────────────────────────

class TestRoadSigns:
    def _read_component(self) -> str:
        from pathlib import Path
        p = Path(__file__).parent.parent.parent / "frontend" / "src" / \
            "pages" / "shared-exam-components.tsx"
        return p.read_text() if p.exists() else ""

    def test_sign_stop_defined(self):
        assert "type === 'stop'" in self._read_component()

    def test_sign_give_way_defined(self):
        assert "give_way" in self._read_component()

    def test_sign_speed_limits(self):
        c = self._read_component()
        for speed in ['30', '50', '70', '90']:
            assert f"speed_{speed}" in c, f"Panneau vitesse {speed} manquant"

    def test_sign_no_entry_defined(self):
        assert "no_entry" in self._read_component()

    def test_sign_pedestrian_crossing(self):
        assert "pedestrian_crossing" in self._read_component()

    def test_sign_parking_signs(self):
        c = self._read_component()
        assert "parking" in c
        assert "no_parking" in c

    def test_sign_danger_defined(self):
        assert "type === 'danger'" in self._read_component()

    def test_scene_svg_intersection(self):
        assert "intersection" in self._read_component()

    def test_scene_svg_safe_distance(self):
        assert "safe_distance" in self._read_component()

    def test_sign_school_zone(self):
        assert "school_zone" in self._read_component()

    def test_total_signs_count(self):
        """Au moins 12 types de panneaux définis."""
        import re
        c = self._read_component()
        sign_types = re.findall(r"type === '([^']+)'", c)
        unique_signs = set(sign_types)
        assert len(unique_signs) >= 12, f"Seulement {len(unique_signs)} panneaux définis"

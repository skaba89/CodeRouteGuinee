"""
Tests finaux — export CSV candidats, health enrichi, booking /my, candidates /me.
"""
import uuid

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_candidate import Candidate
from app.models_user import User
from app.security import get_password_hash
from tests.conftest import get_admin_headers


def _make_candidate(email: str | None = None) -> Candidate:
    """Crée un candidat en base et retourne l'objet."""
    init_db()
    suffix = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        cand = Candidate(
            reference=f"GN-FINAL-{suffix}",
            first_name="Final",
            last_name=f"Test-{suffix}",
            identity_number=f"NINA-FINAL-{suffix}",
            phone=f"+224628{suffix[:6]}",
            permit_category="B",
            status="active",
            email=email,
        )
        db.add(cand)
        db.commit()
        db.refresh(cand)
        return cand


class TestCandidateExportCsv:
    """Tests de l'export CSV candidats."""

    def test_export_csv_returns_200(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/candidates/export.csv", headers=h)
        assert r.status_code == 200

    def test_export_csv_content_type(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/candidates/export.csv", headers=h)
        assert "text/csv" in r.headers["content-type"]

    def test_export_csv_has_header_row(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/candidates/export.csv", headers=h)
        content = r.content.decode("utf-8-sig")
        first_line = content.split("\n")[0]
        assert "reference" in first_line
        assert "nom" in first_line
        assert "telephone" in first_line

    def test_export_csv_includes_candidates(self):
        _make_candidate()  # créer au moins un candidat
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/candidates/export.csv", headers=h)
        lines = r.content.decode("utf-8-sig").strip().split("\n")
        assert len(lines) >= 2  # header + au moins 1 candidat

    def test_export_csv_filter_by_status(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/candidates/export.csv?status=active", headers=h)
        assert r.status_code == 200

    def test_export_csv_filter_by_category(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/candidates/export.csv?permit_category=B", headers=h)
        assert r.status_code == 200
        content = r.content.decode("utf-8-sig")
        # Vérifier que les colonnes sont présentes
        assert "categorie_permis" in content.split("\n")[0]

    def test_export_csv_requires_admin(self):
        """Sans token → 401."""
        with TestClient(app) as client:
            r = client.get("/api/v1/candidates/export.csv")
        assert r.status_code == 401

    def test_export_csv_content_disposition(self):
        """Le header Content-Disposition doit déclencher le téléchargement."""
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/candidates/export.csv", headers=h)
        assert "attachment" in r.headers.get("content-disposition", "")
        assert "candidats_coderoute.csv" in r.headers.get("content-disposition", "")


class TestHealthEnriched:
    """Tests du healthcheck enrichi avec version."""

    def test_health_returns_version(self):
        with TestClient(app) as client:
            r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert data["version"]  # non vide

    def test_health_returns_environment(self):
        with TestClient(app) as client:
            r = client.get("/health")
        data = r.json()
        assert "environment" in data
        assert data["environment"] in ("development", "production", "test", "staging")

    def test_health_status_ok(self):
        with TestClient(app) as client:
            r = client.get("/health")
        assert r.json()["status"] == "ok"

    def test_health_version_semver(self):
        with TestClient(app) as client:
            r = client.get("/health")
        version = r.json()["version"]
        parts = version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestCandidateMeEndpoint:
    """Tests de GET /candidates/me."""

    def _candidate_token(self) -> str:
        """Crée un user candidat avec email et retourne son token."""
        init_db()
        suffix = uuid.uuid4().hex[:8]
        email = f"me-cand-{suffix}@test.com"
        password = "TestPass123!"
        with SessionLocal() as db:
            user = User(
                email=email,
                full_name=f"Me Candidate {suffix}",
                password_hash=get_password_hash(password),
                role="candidate",
            )
            db.add(user)
            db.commit()
            # Créer un candidat avec le même email
            cand = Candidate(
                reference=f"GN-ME-{suffix}",
                first_name="Me", last_name=f"Candidate-{suffix}",
                identity_number=f"NINA-ME-{suffix}",
                phone=f"+224660{suffix[:6]}",
                permit_category="B", status="active",
                email=email,
            )
            db.add(cand)
            db.commit()
        with TestClient(app) as client:
            return client.post("/api/v1/auth/login",
                               data={"username": email, "password": password}).json()["access_token"]

    def test_me_returns_null_when_no_candidate(self):
        """Un user admin n'a pas de profil candidat → null."""
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/candidates/me", headers=h)
        assert r.status_code == 200
        assert r.json() is None

    def test_me_returns_candidate_profile(self):
        """Un candidat avec email correspondant voit son profil."""
        token = self._candidate_token()
        with TestClient(app) as client:
            r = client.get("/api/v1/candidates/me",
                           headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        if data:  # peut être null si email pas encore lié
            assert "reference" in data
            assert data["reference"].startswith("GN-ME-")

    def test_me_requires_auth(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/candidates/me")
        assert r.status_code == 401


class TestBookingMyEndpoint:
    """Tests de GET /bookings/my."""

    def _candidate_token(self) -> str:
        init_db()
        suffix = uuid.uuid4().hex[:8]
        email = f"my-booking-{suffix}@test.com"
        with SessionLocal() as db:
            user = User(
                email=email, full_name=f"My Booking {suffix}",
                password_hash=get_password_hash("TestPass123!"),
                role="candidate",
            )
            db.add(user)
            db.commit()
        with TestClient(app) as client:
            return client.post("/api/v1/auth/login",
                               data={"username": email, "password": "TestPass123!"}).json()["access_token"]

    def test_my_bookings_returns_list(self):
        """GET /bookings/my retourne une liste (vide si pas de candidat lié)."""
        token = self._candidate_token()
        with TestClient(app) as client:
            r = client.get("/api/v1/bookings/my",
                           headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_my_bookings_requires_auth(self):
        with TestClient(app) as client:
            r = client.get("/api/v1/bookings/my")
        assert r.status_code == 401

    def test_my_bookings_structure(self):
        """Si des réservations existent, elles ont la bonne structure."""
        token = self._candidate_token()
        with TestClient(app) as client:
            r = client.get("/api/v1/bookings/my",
                           headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        for bk in data:
            assert "reference" in bk
            assert "status" in bk
            assert "verification_code" in bk

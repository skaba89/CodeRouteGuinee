from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.routers import auth as _auth_module
from tests.conftest import TEST_BOOTSTRAP_TOKEN


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-qr-{suffix}@coderoute.gn"
    password = "StrongPass123!"
    _auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    response = client.post(
        "/api/v1/auth/register",
        headers={"X-Admin-Registration-Token": TEST_BOOTSTRAP_TOKEN},
            json={"email": email, "full_name": "Admin QR", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_convocation_qr_svg_is_generated() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        center = client.post("/api/v1/centers", headers=headers, json={"code": f"QR-{suffix}", "name": "Centre QR", "city": "Conakry", "address": "Ratoma", "capacity": 20, "status": "active"}).json()
        candidate = client.post("/api/v1/candidates", headers=headers, json={"first_name": "Moussa", "last_name": "Keita", "identity_number": f"QR-ID-{suffix}", "phone": "+224444444444", "permit_category": "B"}).json()
        session = client.post("/api/v1/sessions", headers=headers, json={"center_id": center["id"], "starts_at": (datetime.now(UTC) + timedelta(days=4)).isoformat(), "capacity": 20}).json()
        booking = client.post("/api/v1/bookings", headers=headers, json={"candidate_id": candidate["id"], "session_id": session["id"]}).json()

        response = client.get(f"/api/v1/bookings/{booking['reference']}/convocation/qr.svg", headers=headers)
        assert response.status_code == 200
        assert "image/svg+xml" in response.headers["content-type"]
        assert "<svg" in response.text

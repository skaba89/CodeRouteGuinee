from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_convocation_qr_svg_is_generated() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        center = client.post("/api/v1/centers", json={"code": f"QR-{suffix}", "name": "Centre QR", "city": "Conakry", "address": "Ratoma", "capacity": 20, "status": "active"}).json()
        candidate = client.post("/api/v1/candidates", json={"first_name": "Moussa", "last_name": "Keita", "identity_number": f"QR-ID-{suffix}", "phone": "+224444444444", "permit_category": "B"}).json()
        session = client.post("/api/v1/sessions", json={"center_id": center["id"], "starts_at": (datetime.utcnow() + timedelta(days=4)).isoformat(), "capacity": 20}).json()
        booking = client.post("/api/v1/bookings", json={"candidate_id": candidate["id"], "session_id": session["id"]}).json()

        response = client.get(f"/api/v1/bookings/{booking['reference']}/convocation/qr.svg")
        assert response.status_code == 200
        assert "image/svg+xml" in response.headers["content-type"]
        assert "<svg" in response.text

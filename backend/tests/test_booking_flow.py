from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_booking_can_be_created_and_verified() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        center = client.post("/api/v1/centers", json={"code": f"BKG-{suffix}", "name": "Centre booking", "city": "Conakry", "address": "Kaloum", "capacity": 20, "status": "active"}).json()
        candidate = client.post("/api/v1/candidates", json={"first_name": "Ibrahima", "last_name": "Camara", "identity_number": f"BKG-ID-{suffix}", "phone": "+224222222222", "permit_category": "B"}).json()
        session = client.post("/api/v1/sessions", json={"center_id": center["id"], "starts_at": (datetime.utcnow() + timedelta(days=2)).isoformat(), "capacity": 20}).json()

        booking_response = client.post("/api/v1/bookings", json={"candidate_id": candidate["id"], "session_id": session["id"]})
        assert booking_response.status_code == 201
        booking = booking_response.json()
        assert booking["reference"].startswith("GN-CONV-")

        verify_response = client.get(f"/api/v1/bookings/verify/{booking['verification_code']}")
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True

from datetime import datetime, timedelta
from app.time_utils import utc_now
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-booking-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Booking", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_booking_can_be_created_and_verified() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        center = client.post("/api/v1/centers", headers=headers, json={"code": f"BKG-{suffix}", "name": "Centre booking", "city": "Conakry", "address": "Kaloum", "capacity": 20, "status": "active"}).json()
        candidate = client.post("/api/v1/candidates", json={"first_name": "Ibrahima", "last_name": "Camara", "identity_number": f"BKG-ID-{suffix}", "phone": "+224222222222", "permit_category": "B"}).json()
        session = client.post("/api/v1/sessions", headers=headers, json={"center_id": center["id"], "starts_at": (utc_now() + timedelta(days=2)).isoformat(), "capacity": 20}).json()

        booking_response = client.post("/api/v1/bookings", json={"candidate_id": candidate["id"], "session_id": session["id"]})
        assert booking_response.status_code == 201
        booking = booking_response.json()
        assert booking["reference"].startswith("GN-CONV-")

        verify_response = client.get(f"/api/v1/bookings/verify/{booking['verification_code']}")
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True

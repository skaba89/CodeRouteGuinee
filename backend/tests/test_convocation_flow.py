from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-convocation-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Convocation", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_convocation_payload_contains_booking_context() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        center = client.post("/api/v1/centers", headers=headers, json={"code": f"CNV-{suffix}", "name": "Centre convocation", "city": "Conakry", "address": "Matoto", "capacity": 20, "status": "active"}).json()
        candidate = client.post("/api/v1/candidates", headers=headers, json={"first_name": "Fatoumata", "last_name": "Diallo", "identity_number": f"CNV-ID-{suffix}", "phone": "+224333333333", "permit_category": "B"}).json()
        session = client.post("/api/v1/sessions", headers=headers, json={"center_id": center["id"], "starts_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(), "capacity": 20}).json()
        booking = client.post("/api/v1/bookings", headers=headers, json={"candidate_id": candidate["id"], "session_id": session["id"]}).json()

        response = client.get(f"/api/v1/bookings/{booking['reference']}/convocation", headers=headers)
        assert response.status_code == 200
        convocation = response.json()
        assert convocation["reference"] == booking["reference"]
        assert convocation["candidate"]["full_name"] == "Fatoumata Diallo"
        assert convocation["center"]["name"] == "Centre convocation"
        assert convocation["qr_payload"].startswith("CODEROUTE-GN|REF=")

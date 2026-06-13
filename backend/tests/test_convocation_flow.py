from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_convocation_payload_contains_booking_context() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        center = client.post("/api/v1/centers", json={"code": f"CNV-{suffix}", "name": "Centre convocation", "city": "Conakry", "address": "Matoto", "capacity": 20, "status": "active"}).json()
        candidate = client.post("/api/v1/candidates", json={"first_name": "Fatoumata", "last_name": "Diallo", "identity_number": f"CNV-ID-{suffix}", "phone": "+224333333333", "permit_category": "B"}).json()
        session = client.post("/api/v1/sessions", json={"center_id": center["id"], "starts_at": (datetime.utcnow() + timedelta(days=3)).isoformat(), "capacity": 20}).json()
        booking = client.post("/api/v1/bookings", json={"candidate_id": candidate["id"], "session_id": session["id"]}).json()

        response = client.get(f"/api/v1/bookings/{booking['reference']}/convocation")
        assert response.status_code == 200
        convocation = response.json()
        assert convocation["reference"] == booking["reference"]
        assert convocation["candidate"]["full_name"] == "Fatoumata Diallo"
        assert convocation["center"]["name"] == "Centre convocation"
        assert convocation["qr_payload"].startswith("CODEROUTE-GN|REF=")

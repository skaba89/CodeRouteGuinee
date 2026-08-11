from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_payment import Payment
from app.models_session import ExamSession
from app.payment_rules import (
    assert_payment_amount,
    normalize_payment_provider,
    synchronize_booking_from_payment,
)
from app.payment_webhook_security import (
    parse_paydunya_payload,
    verify_paydunya_hash,
    verify_wave_signature,
)
from tests.conftest import get_admin_headers


def _booking_graph() -> tuple[str, str]:
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:10]
    center = Center(
        code=f"PAY-{suffix}",
        name="Centre paiement",
        city="Conakry",
        address="Kaloum",
        capacity=35,
        status="accredited",
    )
    db.add(center)
    db.flush()
    session = ExamSession(
        reference=f"GN-SESSION-PAY-{suffix}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3),
        capacity=35,
        status="planned",
    )
    db.add(session)
    db.flush()
    candidate = Candidate(
        reference=f"GN-CODE-PAY-{suffix}",
        first_name="Mamadou",
        last_name="Diallo",
        identity_number=f"ID-PAY-{suffix}",
        phone="+224622000099",
        permit_category="B",
    )
    db.add(candidate)
    db.flush()
    booking = Booking(
        reference=f"GN-CONV-PAY-{suffix}",
        candidate_id=candidate.id,
        session_id=session.id,
        status="confirmed",
        verification_code=f"VERIFY-{suffix}",
    )
    db.add(booking)
    db.commit()
    booking_ref = booking.reference
    booking_id = booking.id
    db.close()
    return booking_ref, booking_id


def test_unknown_provider_is_never_silently_accepted_as_sandbox() -> None:
    with pytest.raises(HTTPException) as exc_info:
        normalize_payment_provider("totally-unknown-wallet")
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "PAYMENT_PROVIDER_UNSUPPORTED"


def test_legacy_amount_sentinel_is_ignored_but_arbitrary_underpayment_is_rejected() -> None:
    assert_payment_amount(None, 150_000)
    assert_payment_amount(250_000, 150_000)  # compat ancienne UI, pas prix appliqué
    assert_payment_amount(150_000, 150_000)

    with pytest.raises(HTTPException) as exc_info:
        assert_payment_amount(1, 150_000)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "PAYMENT_AMOUNT_MISMATCH"
    assert exc_info.value.detail["expected_amount_gnf"] == 150_000


def test_paid_payment_synchronizes_booking_state_and_reference() -> None:
    booking_ref, _ = _booking_graph()
    db = SessionLocal()
    payment = Payment(
        reference=f"GN-PAY-TEST-{uuid4().hex[:10]}",
        booking_reference=booking_ref,
        amount_gnf=150_000,
        provider="sandbox",
        phone="+224622000099",
        status="paid",
        receipt_number=f"GN-RECEIPT-TEST-{uuid4().hex[:10]}",
        external_reference=f"SANDBOX-{uuid4().hex}",
        paid_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(payment)
    db.flush()
    booking = synchronize_booking_from_payment(db, payment)
    db.commit()
    assert booking is not None
    assert booking.status == "paid"
    assert booking.payment_reference == payment.reference
    db.close()


def test_http_payment_rejects_one_gnf_and_charges_server_tariff(monkeypatch) -> None:
    booking_ref, _ = _booking_graph()
    # Stabilise le tarif pour ce test sans dépendre du cache/table tarifs.
    monkeypatch.setattr("app.routers.payments.resolve_authoritative_amount", lambda db, booking: 150_000)

    with TestClient(app) as client:
        headers = get_admin_headers(client)
        underpay = client.post(
            "/api/v1/payments",
            headers=headers,
            json={
                "booking_reference": booking_ref,
                "amount_gnf": 1,
                "provider": "sandbox",
                "phone": "+224622000099",
            },
        )
        assert underpay.status_code == 422
        assert underpay.json()["detail"]["code"] == "PAYMENT_AMOUNT_MISMATCH"

        paid = client.post(
            "/api/v1/payments",
            headers=headers,
            json={
                "booking_reference": booking_ref,
                "amount_gnf": 250_000,
                "provider": "sandbox",
                "phone": "+224622000099",
            },
        )
        assert paid.status_code == 201
        assert paid.json()["status"] == "paid"
        assert paid.json()["amount_gnf"] == 150_000


def test_wave_signature_uses_timestamped_hmac_and_rejects_replay(monkeypatch) -> None:
    secret = "wave-test-secret-at-least-32-characters"
    monkeypatch.setenv("WAVE_WEBHOOK_SECRET", secret)
    body = b'{"type":"checkout.session.completed","data":{"id":"wave-1"}}'
    timestamp = int(time.time())
    signature = hmac.new(secret.encode(), str(timestamp).encode() + body, hashlib.sha256).hexdigest()

    verify_wave_signature(body, f"t={timestamp},v1={signature}")

    with pytest.raises(HTTPException) as exc_info:
        verify_wave_signature(body, f"t={timestamp - 1000},v1={signature}")
    assert exc_info.value.status_code == 401


def test_paydunya_form_payload_and_master_key_hash_are_verified(monkeypatch) -> None:
    master_key = "paydunya-master-key-at-least-32-characters"
    monkeypatch.setenv("PAYDUNYA_MASTER_KEY", master_key)
    expected_hash = hashlib.sha512(master_key.encode()).hexdigest()
    body = urlencode(
        {
            "data[status]": "completed",
            "data[hash]": expected_hash,
            "data[invoice][token]": "invoice-token-1",
            "data[invoice][total_amount]": "150000",
        }
    ).encode()

    payload = parse_paydunya_payload(body, "application/x-www-form-urlencoded")
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["invoice"]["token"] == "invoice-token-1"
    verify_paydunya_hash(payload)

    payload["data"]["hash"] = "bad"
    with pytest.raises(HTTPException) as exc_info:
        verify_paydunya_hash(payload)
    assert exc_info.value.status_code == 401

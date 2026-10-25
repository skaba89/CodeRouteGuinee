"""
Fixtures partagées pour les tests E2E.
Fournit des helpers d'authentification pour les rôles super_admin, admin, center, candidate.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.models_user import User
from app.security import get_password_hash


def _create_test_user(role: str) -> tuple[str, str]:
    """Crée un utilisateur de test en base et retourne (email, password)."""
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    email = f"test-{role}-{suffix}@coderoute.test"
    password = "TestPass123!"
    try:
        user = User(
            email=email,
            full_name=f"Test {role.title()} {suffix}",
            password_hash=get_password_hash(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()
    return email, password


def get_auth_headers(client: TestClient, role: str = "super_admin") -> dict[str, str]:
    """Retourne les headers Authorization pour un rôle donné."""
    email, password = _create_test_user(role)
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for role {role}: {resp.json()}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_admin_headers(client: TestClient) -> dict[str, str]:
    return get_auth_headers(client, "super_admin")


def get_center_headers(client: TestClient) -> dict[str, str]:
    return get_auth_headers(client, "center")


def get_center_agent_headers(client: TestClient, center_id: str) -> dict[str, str]:
    """Agent de centre rattaché à `center_id` (cloisonnement appliqué par l'API)."""
    init_db()
    email = f"agent-{uuid4().hex[:8]}@coderoute.test"
    password = "AgentPass123!"
    with SessionLocal() as db:
        db.add(User(email=email, full_name="Agent centre", password_hash=get_password_hash(password),
                    role="center", center_id=center_id, is_active=True))
        db.commit()
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def get_candidate_headers(client: TestClient) -> dict[str, str]:
    return get_auth_headers(client, "candidate")


def seed_media_ready_official_bank(
    client: TestClient,
    authority_headers: dict[str, str],
    *,
    marker: str | None = None,
) -> list[str]:
    """Crée une banque de 40 questions réellement éligible à l'examen officiel.

    Les nouveaux gardes d'examen exigent simultanément : distribution officielle,
    statut ``approved`` et média candidat exploitable. Les anciens E2E ne doivent
    pas contourner ces invariants ni dépendre d'un seed implicite.

    ``authority_headers`` doit appartenir à un super_admin afin de pouvoir
    approuver chaque question, comme le ferait l'autorité de validation.
    """
    from app.question_bank_gn import QUESTIONS_GN

    suffix = marker or uuid4().hex[:10]
    question_ids: list[str] = []
    for index, row in enumerate(QUESTIONS_GN):
        create_response = client.post(
            "/api/v1/questions",
            headers=authority_headers,
            json={
                "category": row["category"],
                "text": f"{row['text']} [official-e2e-{suffix}-{index}]",
                "options": row["options"],
                "correct_answer": row["correct_answer"],
                "explanation": row.get("explanation", "Réponse de test officielle"),
                "media_type": "image",
                "media_url": f"https://cdn.example.com/coderoute-tests/{suffix}/{index}.webp",
                "media_alt": f"Illustration officielle de test {index + 1}",
            },
        )
        assert create_response.status_code == 201, create_response.text
        question_id = create_response.json()["id"]
        approve_response = client.post(
            f"/api/v1/questions/{question_id}/approve",
            headers=authority_headers,
        )
        assert approve_response.status_code == 200, approve_response.text
        question_ids.append(question_id)

    assert len(question_ids) == 40
    return question_ids


def verify_candidate_identity(
    client: TestClient,
    candidate_id: str,
    authority_headers: dict[str, str],
    *,
    marker: str | None = None,
) -> None:
    """Passe par le workflow officiel d'identité au lieu de forcer le statut DB."""
    suffix = marker or uuid4().hex[:10]
    submitted = client.post(
        "/api/v1/candidate-identity",
        headers=authority_headers,
        json={
            "candidate_id": candidate_id,
            "document_type": "national_id",
            "document_reference": f"TEST-ID-{suffix}",
        },
    )
    assert submitted.status_code == 201, submitted.text

    decision = client.post(
        f"/api/v1/candidate-identity/{submitted.json()['id']}/decision",
        headers=authority_headers,
        json={
            "status": "verified",
            "reason": "Identité vérifiée pour le scénario E2E officiel",
        },
    )
    assert decision.status_code == 200, decision.text


def prepare_checked_in_booking(
    client: TestClient,
    authority_headers: dict[str, str],
    *,
    check_in: bool = True,
) -> dict:
    """Prépare un candidat prêt à composer, par les endpoints officiels.

    Centre + session imminente (fenêtres d'entrée et d'examen ouvertes) +
    candidat à l'identité vérifiée + réservation payée + entrée contrôlée au
    centre. La banque média doit être préparée séparément
    (``seed_media_ready_official_bank``).
    """
    from datetime import UTC, datetime, timedelta

    suffix = uuid4().hex[:8]
    center = client.post("/api/v1/centers", headers=authority_headers, json={
        "code": f"CTR-{suffix}", "name": "Centre test", "city": "Conakry",
        "address": "Dixinn", "capacity": 20, "status": "active",
    })
    assert center.status_code == 201, center.text
    center = center.json()
    session = client.post("/api/v1/sessions", headers=authority_headers, json={
        "center_id": center["id"],
        "starts_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        "capacity": 20,
    })
    assert session.status_code == 201, session.text
    session = session.json()
    candidate = client.post("/api/v1/candidates", headers=authority_headers, json={
        "first_name": "Aissatou", "last_name": "Bah", "identity_number": f"GN-{suffix}",
        "phone": "+224621111111", "permit_category": "B",
    })
    assert candidate.status_code == 201, candidate.text
    candidate = candidate.json()
    verify_candidate_identity(client, candidate["id"], authority_headers, marker=suffix)
    booking = client.post("/api/v1/bookings", headers=authority_headers, json={
        "candidate_id": candidate["id"], "session_id": session["id"],
    })
    assert booking.status_code == 201, booking.text
    booking = booking.json()
    payment = client.post("/api/v1/payments", headers=authority_headers, json={
        "booking_reference": booking["reference"], "amount_gnf": 150000,
        "provider": "orange_money", "phone": "+224621111111",
    })
    assert payment.status_code == 201, payment.text
    if check_in:
        entry = client.post("/api/v1/entries/validate", headers=authority_headers, json={
            "reference": booking["reference"], "verification_code": booking["verification_code"],
            "center_code": center["code"],
        })
        assert entry.status_code == 200 and entry.json()["allowed"] is True, entry.text
    return {"booking": booking, "candidate": candidate, "session": session, "center": center}


@pytest.fixture(autouse=True)
def clean_test_questions(request):
    """
    Supprime TOUTES les questions actives après chaque test
    pour éviter la pollution de la DB partagée entre les fichiers de tests.
    Les tests qui ont besoin de questions les recrée systématiquement.
    """
    yield
    # Nettoyage agressif après chaque test : supprimer toutes les questions
    try:
        db = SessionLocal()
        from sqlalchemy import delete
        from app.models_question import Question
        db.execute(delete(Question))
        db.commit()
        db.close()
    except Exception:
        pass  # Silencieux

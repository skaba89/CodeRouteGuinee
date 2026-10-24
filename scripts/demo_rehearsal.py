"""Répétition automatique de la démonstration DNTT (scripts/demo.sh check).

Rejoue le parcours candidat complet contre l'API locale, sur la dernière
session live créée par seed_demo_dntt, avec les vrais comptes de démonstration :

  inscription → identité → réservation → paiement Mobile Money → convocation PDF
  → contrôle d'entrée (chef de centre) → examen → résultat
  puis supervision territoriale et intégrité du journal d'audit.

S'arrête à la première étape en échec avec la réponse de l'API.
"""
from __future__ import annotations

import os
import sys
import uuid

import httpx

API = os.getenv("DEMO_API_URL", "http://127.0.0.1:8000/api/v1")
PASSWORD = "CodeRoute2026!"
LIVE_CENTER_CODE = "CRG-KAL-001"

client = httpx.Client(timeout=60)


def check(label: str, response: httpx.Response, expected: tuple[int, ...] = (200, 201, 202)):
    if response.status_code not in expected:
        print(f"❌ {label} → HTTP {response.status_code} {response.text[:500]}")
        sys.exit(1)
    print(f"✅ {label}")
    if "json" in response.headers.get("content-type", ""):
        return response.json()
    return response


def login(email: str, password: str = PASSWORD) -> dict[str, str]:
    token = check(f"connexion {email}", client.post(
        f"{API}/auth/login", data={"username": email, "password": password},
    ))["access_token"]
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    admin = login("admin.national@coderoute.gov.gn")
    chef = login("chef.conakry@coderoute.gov.gn")

    centers = check("liste des centres", client.get(
        f"{API}/centers", headers=admin, params={"search": LIVE_CENTER_CODE},
    ))
    center = next(c for c in centers["items"] if c["code"] == LIVE_CENTER_CODE)
    upcoming = check("sessions à venir du centre", client.get(
        f"{API}/sessions/upcoming-by-center/{center['id']}", headers=admin,
    ))
    live = [s for s in upcoming["items"] if s["reference"].startswith("GN-SESSION-DEMO-LIVE")]
    if not live:
        print("❌ aucune session live à venir : scripts/demo.sh live 15")
        sys.exit(1)
    # La plus proche : c'est celle dont les fenêtres d'entrée et d'examen s'ouvrent en premier.
    session = min(live, key=lambda s: s["starts_at"])
    print(f"   session {session['reference']} à {session['starts_at']}")

    suffix = uuid.uuid4().hex[:6]
    registration = check("inscription publique du candidat", client.post(
        f"{API}/registration/candidate",
        json={
            "first_name": "Répétition", "last_name": f"Démo {suffix}",
            "identity_number": f"GN-REPET-{suffix}", "phone": f"+224622{uuid.uuid4().int % 10**6:06d}",
            "permit_category": "B", "city": "Conakry",
            "email": f"repetition.{suffix}@demo.coderoute.gn", "password": "Candidat2026!",
        },
    ))
    candidate = {"Authorization": f"Bearer {registration['access_token']}"}

    identity = check("dépôt de pièce d'identité", client.post(
        f"{API}/candidate-identity", headers=admin,
        json={"candidate_id": registration["candidate_id"], "document_type": "national_id",
              "document_reference": f"CNI-REPET-{suffix}"},
    ))
    check("validation de l'identité", client.post(
        f"{API}/candidate-identity/{identity['id']}/decision", headers=admin,
        json={"status": "verified", "reason": "Répétition de démonstration"},
    ))

    booking = check("réservation de la session live", client.post(
        f"{API}/bookings/self", headers=candidate, json={"session_id": session["session_id"]},
    ))
    payment = check("paiement Orange Money (sandbox)", client.post(
        f"{API}/payments", headers=candidate,
        json={"booking_reference": booking["reference"], "amount_gnf": 150000,
              "provider": "orange_money", "phone": "+224622000111"},
    ))
    print(f"   reçu {payment['receipt_number']} — {payment['amount_gnf']} GNF")

    pdf = check("convocation PDF", client.get(
        f"{API}/documents/convocations/{booking['reference']}.pdf", headers=candidate,
    ))
    if not pdf.content.startswith(b"%PDF"):
        print("❌ la convocation n'est pas un PDF")
        sys.exit(1)

    entry = check("contrôle d'entrée par le chef de centre", client.post(
        f"{API}/entries/validate", headers=chef,
        json={"reference": booking["reference"], "verification_code": booking["verification_code"],
              "center_code": LIVE_CENTER_CODE},
    ))
    if not entry.get("allowed"):
        print(f"❌ entrée refusée : {entry}")
        sys.exit(1)

    attempt = check("démarrage de l'examen", client.post(
        f"{API}/exams/start-from-booking", headers=candidate,
        json={"booking_reference": booking["reference"]},
    ))
    questions = check("questions de l'examen", client.get(
        f"{API}/exams/{attempt['id']}/questions", headers=candidate,
    ))
    items = questions.get("questions") or questions.get("items") or []
    media_urls = sorted({q.get("media_url") for q in items if q.get("media_url")})
    print(f"   {len(items)} questions, {len(media_urls)} média(s) distinct(s)")
    for url in media_urls:
        media = client.get(url)
        if media.status_code != 200 or not media.headers.get("content-type", "").startswith(("image/", "video/")):
            print(f"❌ média injoignable : {url} → {media.status_code}")
            sys.exit(1)
    print("✅ médias de l'examen joignables")

    answers = {q["id"]: q["options"][0] for q in items}
    result = check("soumission de l'examen", client.post(
        f"{API}/exams/{attempt['id']}/submit", headers=candidate, json={"answers": answers},
    ))
    print(f"   score {result.get('score')}/40 — {'admis' if result.get('passed') else 'ajourné'}")
    check("résultat détaillé", client.get(f"{API}/exams/{attempt['id']}/results", headers=candidate))

    territory = check("supervision territoriale", client.get(f"{API}/dashboard/by-center", headers=admin))
    regions = [r["region"] for r in territory.get("regions", [])]
    print(f"   {len(territory['centers'])} centres, régions : {', '.join(regions)}")

    chain = check("intégrité du journal d'audit", client.get(f"{API}/admin/ops/audit-chain/verify", headers=admin))
    if not chain.get("valid"):
        print(f"❌ chaîne d'audit invalide : {chain}")
        sys.exit(1)
    print(f"   {chain['total_entries']} entrées chaînées, tête n°{chain['head_seq']}")

    print("\n🎉 Répétition réussie : la démonstration peut se dérouler.")


if __name__ == "__main__":
    main()

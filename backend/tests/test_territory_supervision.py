"""Supervision territoriale : rattachement préfecture → région et vue DNTT par région."""
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_center import Center
from app.seed_full import CENTERS
from app.territory import REGIONS, UNKNOWN_REGION, region_for_prefecture
from tests.conftest import get_admin_headers, get_auth_headers, get_candidate_headers


def test_region_lookup_ignores_accents_and_case() -> None:
    assert region_for_prefecture("N'Zérékoré") == "N'Zérékoré"
    assert region_for_prefecture("nzerekore") == UNKNOWN_REGION  # l'apostrophe fait partie du nom
    assert region_for_prefecture("n'zerekore") == "N'Zérékoré"
    assert region_for_prefecture("FORECARIAH") == "Kindia"
    assert region_for_prefecture("  Siguiri ") == "Kankan"
    assert region_for_prefecture("Conakry") == "Conakry"


def test_unknown_or_missing_prefecture_is_flagged() -> None:
    assert region_for_prefecture(None) == UNKNOWN_REGION
    assert region_for_prefecture("") == UNKNOWN_REGION
    assert region_for_prefecture("Paris") == UNKNOWN_REGION


def test_every_seeded_center_maps_to_an_official_region() -> None:
    unmapped = {c["prefecture"] for c in CENTERS if region_for_prefecture(c.get("prefecture")) not in REGIONS}
    assert unmapped == set()
    assert {region_for_prefecture(c["prefecture"]) for c in CENTERS} == set(REGIONS)


def test_by_center_exposes_regions_consistent_with_centers() -> None:
    init_db()
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        db.add_all([
            Center(code=f"TERR-LAB-{suffix}", name="Centre test Labé", city="Labé",
                   prefecture="Labé", address="Centre-ville", status="accredited"),
            Center(code=f"TERR-UNK-{suffix}", name="Centre sans préfecture", city="Inconnue",
                   prefecture=None, address="—", status="pending_audit"),
        ])
        db.commit()

    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/by-center", headers=get_admin_headers(client))
    assert response.status_code == 200, response.text
    body = response.json()

    rows = {row["code"]: row for row in body["centers"]}
    assert rows[f"TERR-LAB-{suffix}"]["region"] == "Labé"
    assert rows[f"TERR-UNK-{suffix}"]["region"] == UNKNOWN_REGION

    regions = {row["region"]: row for row in body["regions"]}
    # Chaque agrégat régional est exactement la somme de ses centres.
    for name, region in regions.items():
        members = [row for row in body["centers"] if row["region"] == name]
        assert region["centers_total"] == len(members)
        for key in ("sessions", "bookings", "exams_passed", "exams_failed", "exams_total", "open_incidents"):
            assert region[key] == sum(row[key] for row in members), (name, key)
    assert sum(r["centers_total"] for r in body["regions"]) == body["national"]["centers_total"]

    # Ordre officiel : Conakry d'abord, région inconnue en dernier.
    ordered = [r["region"] for r in body["regions"]]
    known = [name for name in ordered if name in REGIONS]
    assert known == [name for name in REGIONS if name in known]
    assert ordered[-1] == UNKNOWN_REGION


def test_by_center_is_refused_to_center_and_candidate_roles() -> None:
    init_db()
    with TestClient(app) as client:
        for headers in (get_auth_headers(client, "center"), get_candidate_headers(client)):
            response = client.get("/api/v1/dashboard/by-center", headers=headers)
            assert response.status_code == 403, response.text

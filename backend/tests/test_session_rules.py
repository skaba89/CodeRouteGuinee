"""
Tests des règles métier DNTT pour les sessions d'examen.

Règles testées :
  1. Capacité max 35 candidats par session
  2. Max 3 sessions par semaine par centre
  3. Chevauchement horaire interdit dans le même centre (fenêtre 2h)
  4. Sessions simultanées AUTORISÉES dans des centres différents
  5. 3 centres minimum par commune
  6. Vue calendrier hebdomadaire multi-centres
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_center import Center
from tests.conftest import get_admin_headers

# ── Fixtures ──────────────────────────────────────────────────────────────

def _make_center(commune: str = "TestCommune") -> Center:
    """Crée un centre agréé de test en base."""
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:6]
    center = Center(
        code=f"CTR-TEST-{suffix}",
        name=f"Centre Test {suffix}",
        city="Conakry",
        commune=commune,
        prefecture="Conakry",
        address=f"Rue Test {suffix}",
        capacity=35,
        max_sessions_per_week=3,
        status="accredited",
    )
    db.add(center)
    db.commit()
    db.refresh(center)
    db.close()
    return center


def _next_monday() -> datetime:
    """Retourne le prochain lundi à 09h00."""
    now = datetime.now(UTC).replace(tzinfo=None)
    days_until_monday = (7 - now.weekday()) % 7 or 7
    return (now + timedelta(days=days_until_monday)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )


# ── Règle 1 : Capacité max 35 ─────────────────────────────────────────────

def test_capacity_max_35_accepted() -> None:
    """Une session de exactement 35 candidats est acceptée."""
    center = _make_center()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (_next_monday()).isoformat(),
            "capacity": 35,
        })
        assert r.status_code == 201, f"422 inattendu: {r.text}"
        assert r.json()["capacity"] == 35


def test_capacity_36_refused() -> None:
    """Une session de 36 candidats est refusée (max DNTT = 35)."""
    center = _make_center()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (_next_monday()).isoformat(),
            "capacity": 36,
        })
        assert r.status_code == 422
        assert "35" in r.text or "capacité" in r.text.lower()


def test_capacity_1_accepted() -> None:
    """Une session avec 1 candidat est acceptée (minimum)."""
    center = _make_center()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (_next_monday() + timedelta(hours=1)).isoformat(),
            "capacity": 1,
        })
        assert r.status_code == 201


# ── Règle 2 : Max 3 sessions / semaine / centre ───────────────────────────

def test_three_sessions_same_week_accepted() -> None:
    """Un centre peut avoir exactement 3 sessions la même semaine."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        for day_offset, expected in [(0, 201), (2, 201), (4, 201)]:
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": (monday + timedelta(days=day_offset)).isoformat(),
                "capacity": 35,
            })
            assert r.status_code == expected, \
                f"Session {day_offset+1}/3 : status {r.status_code} attendu {expected} — {r.text[:200]}"


def test_fourth_session_same_week_refused() -> None:
    """La 4ème session dans la même semaine pour un centre est refusée."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        # Créer 3 sessions (lundi, mercredi, vendredi)
        for day in [0, 2, 4]:
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": (monday + timedelta(days=day)).isoformat(),
                "capacity": 35,
            })
            assert r.status_code == 201, f"Setup failed day {day}: {r.text}"

        # La 4ème doit être refusée (samedi de la même semaine)
        r4 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (monday + timedelta(days=5)).isoformat(),
            "capacity": 35,
        })
        assert r4.status_code == 422
        assert "3" in r4.text or "semaine" in r4.text.lower() or "maximum" in r4.text.lower()


def test_same_center_next_week_accepted() -> None:
    """Un centre peut avoir 3 sessions la semaine suivante après avoir eu 3 cette semaine."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        # 3 sessions cette semaine
        for day in [0, 2, 4]:
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": (monday + timedelta(days=day)).isoformat(),
                "capacity": 35,
            })
            assert r.status_code == 201

        # 1ère session semaine suivante → OK
        r_next = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (monday + timedelta(days=7)).isoformat(),
            "capacity": 35,
        })
        assert r_next.status_code == 201, \
            f"Semaine suivante refusée à tort: {r_next.text}"


# ── Règle 3 : Pas de chevauchement dans le même centre ────────────────────

def test_overlapping_sessions_same_center_refused() -> None:
    """Deux sessions dans le même centre à 1h d'intervalle sont refusées."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        # 1ère session lundi 09h00
        r1 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": monday.isoformat(),
            "capacity": 35,
        })
        assert r1.status_code == 201

        # 2ème session 1h après dans le même centre → chevauchement (fenêtre 2h)
        r2 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (monday + timedelta(hours=1)).isoformat(),
            "capacity": 35,
        })
        assert r2.status_code == 422
        assert "chevauche" in r2.text.lower() or "créneau" in r2.text.lower() or "overlap" in r2.text.lower()


def test_sessions_2h_apart_same_center_accepted() -> None:
    """Deux sessions dans le même centre séparées de 2h+ sont acceptées."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r1 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": monday.isoformat(),
            "capacity": 35,
        })
        assert r1.status_code == 201

        # 2ème session 3h après dans le même centre → OK (hors fenêtre 2h)
        # NB : compte pour la semaine (2/3 utilisées)
        r2 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (monday + timedelta(hours=3)).isoformat(),
            "capacity": 35,
        })
        assert r2.status_code == 201, f"Sessions 3h+ à part refusées à tort: {r2.text}"


# ── Règle 4 : Sessions simultanées AUTORISÉES dans centres différents ─────

def test_simultaneous_sessions_different_centers_accepted() -> None:
    """Deux sessions simultanées dans deux centres différents sont autorisées."""
    center_a = _make_center("CommuneA")
    center_b = _make_center("CommuneB")
    monday = _next_monday()

    with TestClient(app) as client:
        h = get_admin_headers(client)
        # Même heure, même jour, deux centres différents → AUTORISÉ
        r_a = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center_a.id,
            "starts_at": monday.isoformat(),
            "capacity": 35,
        })
        r_b = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center_b.id,
            "starts_at": monday.isoformat(),  # Même heure !
            "capacity": 35,
        })
        assert r_a.status_code == 201, f"Centre A refusé: {r_a.text}"
        assert r_b.status_code == 201, \
            f"Centre B refusé à tort (sessions simultanées autorisées): {r_b.text}"


def test_13_simultaneous_sessions_conakry() -> None:
    """
    Simulation réaliste : 13 centres (un par commune de Conakry) peuvent
    lancer des sessions simultanément le même lundi matin.
    C'est le scénario peak du pilote : 13 × 35 = 455 candidats en même temps.
    """
    monday = _next_monday()
    centers = [_make_center(f"Commune{i}") for i in range(13)]

    with TestClient(app) as client:
        h = get_admin_headers(client)
        for i, center in enumerate(centers):
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": monday.isoformat(),  # Tous en même temps
                "capacity": 35,
            })
            assert r.status_code == 201, \
                f"Centre {i+1}/13 refusé à tort: {r.text}"

        # Vérifier que 13 sessions simultanées existent bien en base
        # via le calendrier hebdomadaire
        schedule = client.get(
            "/api/v1/sessions/week-schedule?week_offset=1", headers=h
        )
        assert schedule.status_code == 200
        data = schedule.json()
        # Vérifier qu'il y a bien des sessions ce lundi
        data["days"]["Lundi"]["sessions"]
        # Il devrait y avoir au moins 13 nouvelles sessions ce lundi
        assert data["days"]["Lundi"]["centers_count"] >= 13, \
            f"Attendu 13+ centres le lundi, trouvé: {data['days']['Lundi']['centers_count']}"


# ── Règle 5 : 3 centres minimum par commune ───────────────────────────────

def test_stats_by_commune_compliance() -> None:
    """
    Vérifie que /sessions/stats/by-commune retourne la conformité 3 centres/commune.
    Les données des 13 communes de Conakry sont déjà dans le seed (coderoute.db).
    Ce test vérifie la logique de l'endpoint, pas le seeding.
    """
    COMMUNES_CONAKRY_13 = {
        "Kaloum","Dixinn","Ratoma","Matam","Matoto",
        "Lambanyi","Gbessia","Sonfonia","Tombolia",
        "Kakimbo","Koloma","Nongo","Cosa",
    }
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.get("/api/v1/sessions/stats/by-commune", headers=h)
        assert r.status_code == 200
        stats = r.json()
        assert isinstance(stats, list), "L'endpoint doit retourner une liste"

        # Vérifier que les champs requis sont présents
        for item in stats:
            assert "commune" in item
            assert "centers_count" in item
            assert "compliant_3_centers" in item
            assert "compliance_status" in item

        # Toutes les communes listées avec >= 3 centres doivent être marquées conformes
        for item in stats:
            if item["centers_count"] >= 3:
                assert item["compliant_3_centers"] is True,                     f"Commune {item['commune']} a {item['centers_count']} centres mais non conforme"
            else:
                assert item["compliant_3_centers"] is False,                     f"Commune {item['commune']} a {item['centers_count']} centres mais marquée conforme"

        # Si le seed a été exécuté, les 13 communes Conakry sont présentes et conformes
        by_commune = {s["commune"]: s for s in stats}
        conakry_present = COMMUNES_CONAKRY_13 & set(by_commune.keys())
        for commune in conakry_present:
            assert by_commune[commune]["centers_count"] >= 3,                 f"Commune {commune} du seed : seulement {by_commune[commune]['centers_count']} centres"


def test_capacity_max_35_accepted() -> None:
    """Une session de exactement 35 candidats est acceptée."""
    center = _make_center()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (_next_monday()).isoformat(),
            "capacity": 35,
        })
        assert r.status_code == 201, f"422 inattendu: {r.text}"
        assert r.json()["capacity"] == 35


def test_capacity_36_refused() -> None:
    """Une session de 36 candidats est refusée (max DNTT = 35)."""
    center = _make_center()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (_next_monday()).isoformat(),
            "capacity": 36,
        })
        assert r.status_code == 422
        assert "35" in r.text or "capacité" in r.text.lower()


def test_capacity_1_accepted() -> None:
    """Une session avec 1 candidat est acceptée (minimum)."""
    center = _make_center()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (_next_monday() + timedelta(hours=1)).isoformat(),
            "capacity": 1,
        })
        assert r.status_code == 201


# ── Règle 2 : Max 3 sessions / semaine / centre ───────────────────────────

def test_three_sessions_same_week_accepted() -> None:
    """Un centre peut avoir exactement 3 sessions la même semaine."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        for day_offset, expected in [(0, 201), (2, 201), (4, 201)]:
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": (monday + timedelta(days=day_offset)).isoformat(),
                "capacity": 35,
            })
            assert r.status_code == expected, \
                f"Session {day_offset+1}/3 : status {r.status_code} attendu {expected} — {r.text[:200]}"


def test_fourth_session_same_week_refused() -> None:
    """La 4ème session dans la même semaine pour un centre est refusée."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        # Créer 3 sessions (lundi, mercredi, vendredi)
        for day in [0, 2, 4]:
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": (monday + timedelta(days=day)).isoformat(),
                "capacity": 35,
            })
            assert r.status_code == 201, f"Setup failed day {day}: {r.text}"

        # La 4ème doit être refusée (samedi de la même semaine)
        r4 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (monday + timedelta(days=5)).isoformat(),
            "capacity": 35,
        })
        assert r4.status_code == 422
        assert "3" in r4.text or "semaine" in r4.text.lower() or "maximum" in r4.text.lower()


def test_same_center_next_week_accepted() -> None:
    """Un centre peut avoir 3 sessions la semaine suivante après avoir eu 3 cette semaine."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        # 3 sessions cette semaine
        for day in [0, 2, 4]:
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": (monday + timedelta(days=day)).isoformat(),
                "capacity": 35,
            })
            assert r.status_code == 201

        # 1ère session semaine suivante → OK
        r_next = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (monday + timedelta(days=7)).isoformat(),
            "capacity": 35,
        })
        assert r_next.status_code == 201, \
            f"Semaine suivante refusée à tort: {r_next.text}"


# ── Règle 3 : Pas de chevauchement dans le même centre ────────────────────

def test_overlapping_sessions_same_center_refused() -> None:
    """Deux sessions dans le même centre à 1h d'intervalle sont refusées."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        # 1ère session lundi 09h00
        r1 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": monday.isoformat(),
            "capacity": 35,
        })
        assert r1.status_code == 201

        # 2ème session 1h après dans le même centre → chevauchement (fenêtre 2h)
        r2 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (monday + timedelta(hours=1)).isoformat(),
            "capacity": 35,
        })
        assert r2.status_code == 422
        assert "chevauche" in r2.text.lower() or "créneau" in r2.text.lower() or "overlap" in r2.text.lower()


def test_sessions_2h_apart_same_center_accepted() -> None:
    """Deux sessions dans le même centre séparées de 2h+ sont acceptées."""
    center = _make_center()
    monday = _next_monday()
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r1 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": monday.isoformat(),
            "capacity": 35,
        })
        assert r1.status_code == 201

        # 2ème session 3h après dans le même centre → OK (hors fenêtre 2h)
        # NB : compte pour la semaine (2/3 utilisées)
        r2 = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": (monday + timedelta(hours=3)).isoformat(),
            "capacity": 35,
        })
        assert r2.status_code == 201, f"Sessions 3h+ à part refusées à tort: {r2.text}"


# ── Règle 4 : Sessions simultanées AUTORISÉES dans centres différents ─────

def test_simultaneous_sessions_different_centers_accepted() -> None:
    """Deux sessions simultanées dans deux centres différents sont autorisées."""
    center_a = _make_center("CommuneA")
    center_b = _make_center("CommuneB")
    monday = _next_monday()

    with TestClient(app) as client:
        h = get_admin_headers(client)
        # Même heure, même jour, deux centres différents → AUTORISÉ
        r_a = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center_a.id,
            "starts_at": monday.isoformat(),
            "capacity": 35,
        })
        r_b = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center_b.id,
            "starts_at": monday.isoformat(),  # Même heure !
            "capacity": 35,
        })
        assert r_a.status_code == 201, f"Centre A refusé: {r_a.text}"
        assert r_b.status_code == 201, \
            f"Centre B refusé à tort (sessions simultanées autorisées): {r_b.text}"


def test_13_simultaneous_sessions_conakry() -> None:
    """
    Simulation réaliste : 13 centres (un par commune de Conakry) peuvent
    lancer des sessions simultanément le même lundi matin.
    C'est le scénario peak du pilote : 13 × 35 = 455 candidats en même temps.
    """
    monday = _next_monday()
    centers = [_make_center(f"Commune{i}") for i in range(13)]

    with TestClient(app) as client:
        h = get_admin_headers(client)
        for i, center in enumerate(centers):
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": monday.isoformat(),  # Tous en même temps
                "capacity": 35,
            })
            assert r.status_code == 201, \
                f"Centre {i+1}/13 refusé à tort: {r.text}"

        # Vérifier que 13 sessions simultanées existent bien en base
        # via le calendrier hebdomadaire
        schedule = client.get(
            "/api/v1/sessions/week-schedule?week_offset=1", headers=h
        )
        assert schedule.status_code == 200
        data = schedule.json()
        # Vérifier qu'il y a bien des sessions ce lundi
        data["days"]["Lundi"]["sessions"]
        # Il devrait y avoir au moins 13 nouvelles sessions ce lundi
        assert data["days"]["Lundi"]["centers_count"] >= 13, \
            f"Attendu 13+ centres le lundi, trouvé: {data['days']['Lundi']['centers_count']}"


# ── Règle 5 : 3 centres minimum par commune ───────────────────────────────

def test_commune_compliance_field_present() -> None:
    """L'endpoint stats/by-commune retourne les champs de conformité."""
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.get("/api/v1/sessions/stats/by-commune", headers=h)
        assert r.status_code == 200
        stats = r.json()
        if stats:
            first = stats[0]
            assert "commune" in first
            assert "centers_count" in first
            assert "compliant_3_centers" in first
            assert "compliance_status" in first


# ── Règle 6 : Vue calendrier multi-centres ────────────────────────────────

def test_week_schedule_shows_concurrent_sessions() -> None:
    """
    GET /sessions/week-schedule retourne toutes les sessions par jour,
    avec le nombre de centres simultanément actifs.
    """
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.get("/api/v1/sessions/week-schedule?week_offset=1", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "days" in data
        assert "Lundi" in data["days"]
        assert "total_sessions" in data
        assert "simultaneous_peak" in data
        # simultaneous_peak = nb max de sessions le même jour (multi-centres)
        assert isinstance(data["simultaneous_peak"], int)


def test_week_schedule_filter_by_prefecture() -> None:
    """Le calendrier peut être filtré par préfecture."""
    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.get(
            "/api/v1/sessions/week-schedule?week_offset=0&prefecture=Conakry",
            headers=h
        )
        assert r.status_code == 200
        data = r.json()
        # Toutes les sessions doivent être de Conakry
        for day_data in data["days"].values():
            for session in day_data["sessions"]:
                assert session.get("prefecture") in (None, "Conakry"), \
                    f"Session d'une autre préfecture dans le filtre Conakry: {session}"


# ── Règle 7 : Centre non agréé ne peut pas organiser d'examen ─────────────

def test_non_accredited_center_refused() -> None:
    """Un centre en statut 'pending_audit' ne peut pas organiser de session."""
    db = SessionLocal()
    suffix = uuid4().hex[:6]
    center = Center(
        code=f"CTR-PENDING-{suffix}",
        name=f"Centre Pending {suffix}",
        city="Conakry",
        commune="Kaloum",
        prefecture="Conakry",
        address="Rue Test",
        capacity=35,
        max_sessions_per_week=3,
        status="pending_audit",  # PAS agréé
    )
    db.add(center)
    db.commit()
    db.refresh(center)
    center_id = center.id
    db.close()

    with TestClient(app) as client:
        h = get_admin_headers(client)
        r = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center_id,
            "starts_at": _next_monday().isoformat(),
            "capacity": 35,
        })
        assert r.status_code == 422
        assert "agréé" in r.text.lower() or "accredited" in r.text.lower() or "statut" in r.text.lower()


# ── Règle 8 : Statut de remplissage en temps réel ─────────────────────────

def test_capacity_status_tracks_bookings() -> None:
    """GET /sessions/{id}/capacity-status reflète les réservations en temps réel."""
    center = _make_center()
    monday = _next_monday()

    with TestClient(app) as client:
        h = get_admin_headers(client)
        session = client.post("/api/v1/sessions", headers=h, json={
            "center_id": center.id,
            "starts_at": monday.isoformat(),
            "capacity": 35,
        }).json()

        status = client.get(
            f"/api/v1/sessions/{session['id']}/capacity-status", headers=h
        ).json()

        assert status["capacity"] == 35
        assert status["booked"] == 0
        assert status["available"] == 35
        assert status["fill_rate_pct"] == 0.0
        assert status["is_full"] is False

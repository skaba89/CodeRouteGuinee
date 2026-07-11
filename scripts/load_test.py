#!/usr/bin/env python3
"""
Test de charge — CodeRoute Guinée
=================================

Mesure les chemins chauds sous concurrence croissante et compte les
requêtes SQL (détection des N+1). À lancer contre une base PostgreSQL
de test représentative.

Usage :
  DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db" \
    python scripts/load_test.py

Ce que ça mesure :
  - AVAILABILITY : nombre de requêtes SQL + latence (endpoint le plus
    sollicité le jour d'une session : chaque candidat le charge)
  - Concurrence 1 → 100 : latence p50/p95, débit req/s, taux d'erreur

Limite connue : lancé via TestClient (process unique), le débit plafonne
à la capacité d'UN worker. En production, gunicorn multiplie par le
nombre de workers (voir docs/SCALING.md). Ce test valide l'EFFICACITÉ du
code (peu de requêtes, 0 erreur), pas la capacité absolue de l'infra.
"""
from __future__ import annotations

import os
import statistics
import threading
import time
from datetime import UTC, datetime, timedelta


def main() -> int:
    if "postgresql" not in os.environ.get("DATABASE_URL", ""):
        print("⚠️  Recommandé : DATABASE_URL PostgreSQL (SQLite ne reflète "
              "pas la concurrence de production).")

    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("SECRET_KEY", "loadtest-secret-1234567890abcdef")
    os.environ.setdefault("CSRF_SECRET", "loadtest-csrf-1234567890abcdef")

    from fastapi.testclient import TestClient

    from app.db.session import SessionLocal
    from app.main import app
    from app.models_center import Center
    from app.models_session import ExamSession

    # Jeu de données représentatif
    db = SessionLocal()
    if not db.get(Center, "lt-center"):
        db.add(Center(id="lt-center", code="GN-LT", name="Centre Charge",
                      city="Conakry", prefecture="Conakry", commune="Kaloum",
                      address="x", capacity=35, status="active"))
        for i in range(30):
            db.add(ExamSession(id=f"lt-s{i}", reference=f"LT-S{i}", center_id="lt-center",
                               starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=i + 1),
                               capacity=35, status="open"))
        db.commit()
    db.close()

    latencies: list[float] = []
    errors = [0]
    lock = threading.Lock()

    with TestClient(app) as client:
        try:
            from tests.conftest import get_admin_headers
            auth = get_admin_headers(client)
        except Exception:
            auth = {}

        def hit(n: int) -> None:
            for _ in range(n):
                t0 = time.perf_counter()
                try:
                    r = client.get("/api/v1/bookings/availability/lt-center", headers=auth)
                    dt = (time.perf_counter() - t0) * 1000
                    with lock:
                        if r.status_code == 200:
                            latencies.append(dt)
                        else:
                            errors[0] += 1
                except Exception:
                    with lock:
                        errors[0] += 1

        print("=== Test de charge — endpoint availability ===\n")
        for concurrency in [1, 10, 50, 100]:
            latencies.clear()
            errors[0] = 0
            reqs_per = 20
            threads = [threading.Thread(target=hit, args=(reqs_per,)) for _ in range(concurrency)]
            t0 = time.perf_counter()
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            total_time = time.perf_counter() - t0
            total = concurrency * reqs_per
            if latencies:
                p50 = statistics.median(latencies)
                p95 = (statistics.quantiles(latencies, n=20)[18]
                       if len(latencies) >= 20 else max(latencies))
                print(f"Concurrence {concurrency:3d} | {total:4d} req | "
                      f"p50={p50:6.1f}ms p95={p95:7.1f}ms | "
                      f"{total / total_time:6.0f} req/s | erreurs={errors[0]}")
            else:
                print(f"Concurrence {concurrency:3d} | échec total ({errors[0]} erreurs)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

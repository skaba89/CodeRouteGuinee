"""Contrat agent Edge ↔ API : chaque URL appelée par l'agent est montée.

Régression : `GET /center-edge/lease-signing-key` avait disparu quand la garde
de poste a remplacé le routeur hors ligne ; l'agent ne pouvait plus vérifier
la signature des baux d'examen hors ligne.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.main import app

EDGE_AGENT = Path(__file__).resolve().parents[2] / "edge_agent" / "coderoute_edge"
_API_PATH = re.compile(r"""["'](/api/v1/[A-Za-z0-9_/{}.-]+)["']""")


def _agent_paths() -> set[str]:
    paths: set[str] = set()
    for source in EDGE_AGENT.glob("*.py"):
        paths |= set(_API_PATH.findall(source.read_text(encoding="utf-8")))
    return paths


def test_every_path_called_by_the_edge_agent_is_mounted() -> None:
    called = _agent_paths()
    assert "/api/v1/center-edge/lease-signing-key" in called  # le contrat est bien lu
    mounted = {getattr(route, "path", "") for route in app.routes}
    missing = sorted(path for path in called if path not in mounted)
    assert missing == [], f"routes appelées par l'agent Edge mais absentes de l'API : {missing}"

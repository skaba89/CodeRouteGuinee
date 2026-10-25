"""Aucun service Docker ne doit écouter sur toutes les interfaces de l'hôte.

Régression : la stack de démo publiait PostgreSQL, l'API et le frontend sur
0.0.0.0 d'un VPS de production. Docker contourne ufw pour les ports publiés :
ils étaient joignables depuis Internet malgré le pare-feu.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_COMPOSE_FILES = ["docker-compose.yml", "docker-compose.dev.yml", "docker-compose.demo.yml"]
LOOPBACK_PREFIXES = ("${BIND_ADDRESS:-127.0.0.1}:", "127.0.0.1:")


def _port_mappings(path: Path) -> list[str]:
    """Entrées de listes `ports:` (format court), sans dépendre de PyYAML."""
    mappings: list[str] = []
    in_ports = False
    ports_indent = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if re.match(r"ports:\s*(!reset\s*\[\]\s*)?$", stripped):
            in_ports, ports_indent = True, indent
            continue
        if in_ports:
            if indent > ports_indent and stripped.startswith("- "):
                mappings.append(stripped[2:].strip().strip("\"'"))
                continue
            in_ports = False
    return mappings


def test_local_compose_files_bind_ports_to_loopback_only() -> None:
    offenders = {
        name: [m for m in _port_mappings(ROOT / name) if not m.startswith(LOOPBACK_PREFIXES)]
        for name in LOCAL_COMPOSE_FILES
        if (ROOT / name).exists()
    }
    assert not any(offenders.values()), f"Ports publiés hors 127.0.0.1 : {offenders}"


def test_vps_production_compose_publishes_no_port() -> None:
    compose = (ROOT / "deploy" / "vps" / "docker-compose.vps.yml").read_text(encoding="utf-8")
    assert not re.search(r"^\s+ports:", compose, re.MULTILINE), (
        "La production VPS ne publie aucun port : seul le Caddy d'Academy est exposé."
    )


def test_port_parser_detects_public_binding(tmp_path: Path) -> None:
    sample = tmp_path / "compose.yml"
    sample.write_text('services:\n  db:\n    ports:\n      - "5435:5432"\n', encoding="utf-8")
    assert _port_mappings(sample) == ["5435:5432"]

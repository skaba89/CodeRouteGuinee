from __future__ import annotations

from pathlib import Path


DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "systemd"


def test_edge_daemon_cannot_write_root_owned_release_tree() -> None:
    unit = (DEPLOY / "coderoute-edge.service").read_text(encoding="utf-8")
    assert "User=coderoute-edge" in unit
    assert "NoNewPrivileges=true" in unit
    assert "ReadOnlyPaths=/etc/coderoute-edge /opt/coderoute-edge/releases" in unit
    write_line = next(line for line in unit.splitlines() if line.startswith("ReadWritePaths="))
    assert "/opt/coderoute-edge/releases" not in write_line
    assert "/var/lib/coderoute-edge" in write_line
    assert "/var/cache/coderoute-edge" in write_line
    assert "docker.sock" not in unit


def test_root_updater_has_no_shell_or_docker_socket_and_only_expected_write_paths() -> None:
    unit = (DEPLOY / "coderoute-edge-updater.service").read_text(encoding="utf-8")
    assert "User=root" in unit
    assert "ExecStart=/opt/coderoute-edge/releases/current/.venv/bin/python" in unit
    assert "/bin/sh" not in unit and "/bin/bash" not in unit
    assert "docker.sock" not in unit
    write_line = next(line for line in unit.splitlines() if line.startswith("ReadWritePaths="))
    assert "/opt/coderoute-edge/releases" in write_line
    assert "/var/lib/coderoute-edge/release-staging" in write_line
    assert "ReadOnlyPaths=/etc/coderoute-edge" in unit


def test_update_timer_is_rate_limited_and_randomized() -> None:
    timer = (DEPLOY / "coderoute-edge-updater.timer").read_text(encoding="utf-8")
    assert "OnUnitActiveSec=15min" in timer
    assert "RandomizedDelaySec=2min" in timer
    assert "Persistent=true" in timer

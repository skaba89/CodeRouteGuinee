"""Régression : le chaînage d'audit doit être actif hors de l'API.

Avant correction, l'écouteur HMAC n'était enregistré qu'à l'import de
app.main : un seed, un script d'import ou bootstrap_admin écrivait des lignes
non chaînées, et la vérification d'intégrité échouait (legacy_anchor_mismatch).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

_SCRIPT = """
import sys
import app.models_audit  # seul import d'un écrivain du journal, sans app.main
from sqlalchemy import event
from sqlalchemy.orm import Session
assert "app.main" not in sys.modules
# Vérifié AVANT tout import explicite, qui enregistrerait l'écouteur lui-même.
assert "app.audit_chain" in sys.modules, "app.models_audit doit charger le chaînage"
from app.audit_chain import _chain_new_audit_rows
assert event.contains(Session, "before_flush", _chain_new_audit_rows)
print("chained")
"""


def test_importing_audit_model_registers_chain_listener() -> None:
    env = {**os.environ, "PYTHONPATH": str(BACKEND)}
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "chained"

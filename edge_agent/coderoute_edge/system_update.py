from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from .config import EdgeAgentConfig
from .maintenance import assert_safe_maintenance
from .updater import apply_verified_release, rollback_to_previous

RestartService = Callable[[str], None]
HealthProbe = Callable[[str, int, Path | None], dict[str, Any]]


def _json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _restart_systemd(service_name: str) -> None:
    subprocess.run(
        ["systemctl", "restart", service_name],
        check=True,
        timeout=45,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _probe_health(public_url: str, timeout_seconds: int, ca_path: Path | None) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error = "health-check non exécuté"
    verify: bool | str = str(ca_path) if ca_path else True
    while time.monotonic() < deadline:
        try:
            with httpx.Client(verify=verify, timeout=5.0, follow_redirects=False) as client:
                response = client.get(f"{public_url.rstrip('/')}/health")
            if response.status_code == 200:
                body = response.json()
                if isinstance(body, dict) and body.get("status") == "ok":
                    return body
                last_error = "payload /health invalide"
            else:
                last_error = f"HTTP {response.status_code}"
        except Exception as exc:  # le service peut être en plein restart
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"Health-check Edge expiré : {last_error}")


def _read_staged(release_root: Path) -> dict[str, Any]:
    path = release_root / "staged.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Aucune release Edge vérifiée n'est prête pour la transaction système") from exc
    if not isinstance(data, dict) or data.get("verified") is not True:
        raise RuntimeError("État de staging Edge invalide")
    return data


def _failed_receipt(
    release_root: Path,
    staged: dict[str, Any],
    *,
    error: str,
    rollback: dict[str, Any] | None,
) -> dict[str, Any]:
    receipt = {
        "release_id": str(staged.get("release_id") or ""),
        "software_version": str(staged.get("software_version") or ""),
        "artifact_sha256": str(staged.get("artifact_sha256") or ""),
        "result": "failed",
        "error": error[:1000],
        "rollback_confirmed": bool(rollback),
        "rollback_release_id": rollback.get("release_id") if rollback else None,
        "rollback_version": rollback.get("software_version") if rollback else None,
    }
    _json_atomic(release_root / "install-receipt.json", receipt)
    return receipt


def apply_system_update_transaction(
    config: EdgeAgentConfig,
    *,
    emergency_window_bypass: bool = False,
    restart_service: RestartService = _restart_systemd,
    health_probe: HealthProbe = _probe_health,
) -> dict[str, Any]:
    """Applique une release vérifiée comme transaction système locale.

    L'ordre est volontairement strict : fenêtre -> quiescence -> re-hash/extract
    P8 -> restart -> health/version. Un échec post-restart déclenche un rollback
    local puis un second health-check. Le reçu final reste `failed` pour la
    release fautive afin que la DNTT mette automatiquement son rollout en pause.
    """
    state = assert_safe_maintenance(
        config.database_path,
        config.maintenance_windows,
        config.maintenance_timezone,
        bypass_window=emergency_window_bypass,
    )
    staged = _read_staged(config.release_dir)
    expected_version = str(staged.get("software_version") or "")
    if not expected_version:
        raise RuntimeError("Version staged absente")

    try:
        installed = apply_verified_release(config.release_dir)
    except Exception as exc:
        failed = _failed_receipt(config.release_dir, staged, error=f"apply: {exc}", rollback=None)
        return {"ok": False, "phase": "apply", "receipt": failed, "quiescent": state.quiescent}

    try:
        restart_service(config.systemd_service_name)
        health = health_probe(config.public_url, config.healthcheck_timeout_seconds, config.healthcheck_ca_path)
        running_version = str(health.get("software_version") or "")
        if running_version != expected_version:
            raise RuntimeError(
                f"Version démarrée {running_version or 'inconnue'} différente de la version attendue {expected_version}"
            )
        return {
            "ok": True,
            "phase": "confirmed",
            "receipt": installed,
            "health": health,
            "quiescent": state.quiescent,
        }
    except Exception as primary_exc:
        rollback_receipt: dict[str, Any] | None = None
        rollback_error: Exception | None = None
        try:
            rollback_receipt = rollback_to_previous(config.release_dir)
            restart_service(config.systemd_service_name)
            rollback_health = health_probe(config.public_url, config.healthcheck_timeout_seconds, config.healthcheck_ca_path)
            rollback_version = str(rollback_health.get("software_version") or "")
            expected_rollback = str(rollback_receipt.get("software_version") or "")
            if rollback_version != expected_rollback:
                raise RuntimeError(
                    f"Rollback démarré en {rollback_version or 'inconnue'} au lieu de {expected_rollback}"
                )
        except Exception as exc:
            rollback_error = exc

        error = f"post-restart: {primary_exc}"
        if rollback_error is not None:
            error += f"; rollback: {rollback_error}"
            rollback_receipt = None
        failed = _failed_receipt(config.release_dir, staged, error=error, rollback=rollback_receipt)
        return {
            "ok": False,
            "phase": "rolled_back" if rollback_receipt else "critical",
            "receipt": failed,
            "rollback": rollback_receipt,
            "quiescent": state.quiescent,
        }

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from .config import EdgeAgentConfig
from .maintenance import assert_safe_maintenance
from .release_trust import verify_staged_release_for_root
from .updater import apply_verified_release, rollback_to_previous

RestartService = Callable[[str], None]
HealthProbe = Callable[[str, int, Path | None], dict[str, Any]]
RuntimePrepare = Callable[[Path, str], dict[str, Any]]
StagedVerifier = Callable[[dict[str, Any], Path], dict[str, Any]]


def _json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        except Exception as exc:
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"Health-check Edge expiré : {last_error}")


def _read_staged(staging_root: Path) -> dict[str, Any]:
    path = staging_root / "staged.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Aucune release Edge vérifiée n'est prête pour la transaction système") from exc
    if not isinstance(data, dict) or data.get("verified") is not True:
        raise RuntimeError("État de staging Edge invalide")
    return data


def _verify_staged_with_local_trust(staged: dict[str, Any], staging_root: Path) -> dict[str, Any]:
    trust_store = Path(os.environ.get(
        "CODEROUTE_EDGE_RELEASE_TRUST_PATH",
        "/etc/coderoute-edge/release-trust.json",
    ))
    return verify_staged_release_for_root(
        staged,
        release_root=staging_root,
        trust_store_path=trust_store,
    )


def _failed_receipt(
    staging_root: Path,
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
    _json_atomic(staging_root / "install-receipt.json", receipt)
    return receipt


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _copy_into_root_workspace(staged: dict[str, Any], staging_root: Path, release_root: Path) -> dict[str, Any]:
    if staging_root.resolve() == release_root.resolve():
        return staged
    release_root.mkdir(parents=True, exist_ok=True)
    release_id = str(staged.get("release_id") or "")
    source = Path(str(staged.get("artifact_path") or "")).resolve()
    expected_source = (staging_root / f"{release_id}.tar.gz").resolve()
    if source != expected_source or not source.is_file():
        raise RuntimeError("Artefact de staging introuvable ou hors staging approuvé")
    destination = release_root / f"{release_id}.tar.gz"
    tmp = release_root / f".root-copy-{release_id}.tmp"
    with source.open("rb") as src, tmp.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())
    os.replace(tmp, destination)
    root_state = dict(staged)
    root_state["artifact_path"] = str(destination.resolve())
    _json_atomic(release_root / "staged.json", root_state)
    return root_state


def _handoff_receipt(staging_root: Path, release_root: Path, receipt: dict[str, Any]) -> None:
    _json_atomic(staging_root / "install-receipt.json", receipt)
    (staging_root / "staged.json").unlink(missing_ok=True)
    (release_root / "staged.json").unlink(missing_ok=True)


def _prepare_offline_runtime(target_root: Path, runtime_python: str) -> dict[str, Any]:
    edge_root = target_root / "edge_agent"
    lock = edge_root / "requirements.runtime.lock"
    wheelhouse = edge_root / "wheelhouse"
    if not lock.is_file() or not wheelhouse.is_dir() or not any(wheelhouse.glob("*.whl")):
        raise RuntimeError("Runtime P9 incomplet : lock hashé ou wheelhouse absent de l'artefact signé")

    lock_sha = _sha256_file(lock)
    venv = target_root / ".venv"
    marker = target_root / ".runtime-ready.json"
    if marker.is_file() and (venv / "bin" / "python").is_file():
        try:
            previous = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
        if previous.get("requirements_lock_sha256") == lock_sha:
            return previous

    if venv.exists():
        shutil.rmtree(venv)
    subprocess.run(
        [runtime_python, "-m", "venv", str(venv)],
        check=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    pip = venv / "bin" / "pip"
    subprocess.run(
        [
            str(pip),
            "install",
            "--disable-pip-version-check",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "--require-hashes",
            "-r",
            str(lock),
        ],
        check=True,
        timeout=300,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    ready = {
        "requirements_lock_sha256": lock_sha,
        "python": runtime_python,
        "venv_python": str((venv / "bin" / "python").resolve()),
        "wheel_count": len(list(wheelhouse.glob("*.whl"))),
    }
    _json_atomic(marker, ready)
    return ready


def apply_system_update_transaction(
    config: EdgeAgentConfig,
    *,
    emergency_window_bypass: bool = False,
    restart_service: RestartService = _restart_systemd,
    health_probe: HealthProbe = _probe_health,
    runtime_prepare: RuntimePrepare = _prepare_offline_runtime,
    staged_verifier: StagedVerifier = _verify_staged_with_local_trust,
) -> dict[str, Any]:
    """Applique une release depuis le staging non privilégié vers l'arbre root-owned."""
    state = assert_safe_maintenance(
        config.database_path,
        config.maintenance_windows,
        config.maintenance_timezone,
        bypass_window=emergency_window_bypass,
    )
    staging_root = getattr(config, "release_staging_dir", None) or config.release_dir
    staged = _read_staged(staging_root)
    root_verification = staged_verifier(staged, staging_root)
    expected_version = str(root_verification.get("software_version") or staged.get("software_version") or "")
    if not expected_version:
        raise RuntimeError("Version staged absente")

    try:
        _copy_into_root_workspace(staged, staging_root, config.release_dir)
        installed = apply_verified_release(config.release_dir)
        target_root = Path(str(installed.get("current_path") or ""))
        runtime = runtime_prepare(target_root, config.runtime_python)
    except Exception as exc:
        rollback_receipt: dict[str, Any] | None = None
        try:
            rollback_receipt = rollback_to_previous(config.release_dir)
        except Exception:
            rollback_receipt = None
        failed = _failed_receipt(
            staging_root,
            staged,
            error=f"apply/runtime: {exc}",
            rollback=rollback_receipt,
        )
        _handoff_receipt(staging_root, config.release_dir, failed)
        return {
            "ok": False,
            "phase": "runtime" if rollback_receipt else "critical",
            "receipt": failed,
            "rollback": rollback_receipt,
            "root_verification": root_verification,
            "quiescent": state.quiescent,
        }

    try:
        restart_service(config.systemd_service_name)
        health = health_probe(config.public_url, config.healthcheck_timeout_seconds, config.healthcheck_ca_path)
        running_version = str(health.get("software_version") or "")
        if running_version != expected_version:
            raise RuntimeError(
                f"Version démarrée {running_version or 'inconnue'} différente de la version attendue {expected_version}"
            )
        _handoff_receipt(staging_root, config.release_dir, installed)
        return {
            "ok": True,
            "phase": "confirmed",
            "receipt": installed,
            "root_verification": root_verification,
            "runtime": runtime,
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
        failed = _failed_receipt(staging_root, staged, error=error, rollback=rollback_receipt)
        _handoff_receipt(staging_root, config.release_dir, failed)
        return {
            "ok": False,
            "phase": "rolled_back" if rollback_receipt else "critical",
            "receipt": failed,
            "rollback": rollback_receipt,
            "root_verification": root_verification,
            "quiescent": state.quiescent,
        }

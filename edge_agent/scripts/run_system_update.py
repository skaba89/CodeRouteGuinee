from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx

from coderoute_edge.config import EdgeAgentConfig
from coderoute_edge.system_update import apply_system_update_transaction


def _write_json_atomic(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _refresh_install_authorization(config: EdgeAgentConfig, staging_root: Path) -> tuple[bool, str]:
    staged_path = staging_root / "staged.json"
    try:
        staged = json.loads(staged_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "staging_unreadable"
    if not isinstance(staged, dict):
        return False, "staging_invalid"

    verify: bool | str = str(config.healthcheck_ca_path) if config.healthcheck_ca_path else True
    try:
        with httpx.Client(verify=verify, timeout=15.0, follow_redirects=False) as client:
            response = client.post(
                f"{config.public_url.rstrip('/')}/operator/release/check",
                headers={"X-Edge-Operator-Token": config.operator_token},
            )
    except Exception as exc:
        return False, f"central_reauthorization_unavailable:{exc}"
    if response.status_code != 200:
        return False, f"central_reauthorization_http_{response.status_code}"
    try:
        offer = response.json()
    except ValueError:
        return False, "central_reauthorization_invalid_json"
    if not isinstance(offer, dict) or not offer.get("update_available"):
        return False, "release_no_longer_authorized"

    bundle = offer.get("release") if isinstance(offer.get("release"), dict) else {}
    manifest = bundle.get("manifest") if isinstance(bundle.get("manifest"), dict) else {}
    offered_release_id = str(bundle.get("release_id") or manifest.get("release_id") or "")
    offered_action = str(offer.get("action") or "install")
    offered_source = str(offer.get("source_release_id") or "") or None
    staged_source = str(staged.get("source_release_id") or "") or None
    if (
        offered_release_id != str(staged.get("release_id") or "")
        or offered_action != str(staged.get("action") or "install")
        or offered_source != staged_source
    ):
        return False, "staged_release_not_currently_authorized"

    authorization = offer.get("install_authorization")
    if not isinstance(authorization, dict):
        return False, "fresh_install_authorization_missing"
    staged["install_authorization"] = authorization
    _write_json_atomic(staged_path, staged)
    return True, "authorized"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Applique une release Center Edge vérifiée avec fenêtre de maintenance, restart, health-check et rollback."
    )
    parser.add_argument(
        "--emergency-window-bypass",
        action="store_true",
        help="Ignore uniquement la fenêtre horaire. Les examens actifs et journaux non synchronisés restent bloquants.",
    )
    args = parser.parse_args()
    config = EdgeAgentConfig.from_env()
    staging_root = config.release_staging_dir or config.release_dir
    if not (staging_root / "staged.json").is_file():
        print(json.dumps({"ok": True, "phase": "skipped", "reason": "no_staged_release"}))
        return 0

    authorized, reason = _refresh_install_authorization(config, staging_root)
    if not authorized:
        # Fail closed sans bruit systemd : le timer re-vérifiera plus tard. Une
        # pause/révocation centrale doit donc bloquer immédiatement un staging
        # ancien sans transformer une panne WAN en faux incident local.
        print(json.dumps({"ok": True, "phase": "skipped", "reason": reason}, ensure_ascii=False))
        return 0

    try:
        result = apply_system_update_transaction(
            config,
            emergency_window_bypass=args.emergency_window_bypass,
        )
    except RuntimeError as exc:
        message = str(exc)
        if "hors fenêtre" in message or "Mise à jour Edge bloquée" in message:
            print(json.dumps({"ok": True, "phase": "skipped", "reason": message}, ensure_ascii=False))
            return 0
        print(json.dumps({"ok": False, "phase": "preflight", "error": message}, ensure_ascii=False))
        return 30
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result.get("ok"):
        return 0
    return 20 if result.get("phase") == "rolled_back" else 30


if __name__ == "__main__":
    raise SystemExit(main())

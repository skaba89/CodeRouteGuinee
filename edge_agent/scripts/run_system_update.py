from __future__ import annotations

import argparse
import json

from coderoute_edge.config import EdgeAgentConfig
from coderoute_edge.system_update import apply_system_update_transaction


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
    if not (config.release_dir / "staged.json").is_file():
        print(json.dumps({"ok": True, "phase": "skipped", "reason": "no_staged_release"}))
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

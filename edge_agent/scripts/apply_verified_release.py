from __future__ import annotations

import argparse
from pathlib import Path

from coderoute_edge.updater import apply_verified_release, rollback_to_previous


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Applique uniquement une release Center Edge déjà téléchargée et vérifiée par l'agent non privilégié."
    )
    parser.add_argument(
        "--release-root",
        default=".coderoute-edge/releases",
        help="Répertoire de staging/versions Center Edge",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rebascule vers la version précédemment vérifiée",
    )
    args = parser.parse_args()

    root = Path(args.release_root)
    result = rollback_to_previous(root) if args.rollback else apply_verified_release(root)
    print(
        f"release_id={result['release_id']} version={result['software_version']} "
        f"result={result['result']} current={result['current_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

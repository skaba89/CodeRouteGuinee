from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import tarfile
from pathlib import Path

_VERSION_RE = re.compile(r"^edge-agent-[0-9]+\.[0-9]+\.[0-9]+(?:[-._A-Za-z0-9]*)?$")
_EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".coderoute-edge", "tests"}
_ALLOWED_ROOT_FILES = {
    "requirements.txt",
    "requirements.runtime.txt",
    "requirements.runtime.lock",
    "Dockerfile",
}
_ALLOWED_SCRIPT_FILES = {"apply_verified_release.py", "run_system_update.py"}


def _included_files(edge_root: Path) -> list[Path]:
    files: list[Path] = []
    package = edge_root / "coderoute_edge"
    if not package.is_dir():
        raise RuntimeError(f"Package Edge introuvable : {package}")
    for path in package.rglob("*"):
        if not path.is_file() or any(part in _EXCLUDED_PARTS for part in path.parts):
            continue
        if path.suffix in {".py", ".json"} or path.name in {"py.typed"}:
            files.append(path)
    for name in sorted(_ALLOWED_ROOT_FILES):
        path = edge_root / name
        if path.is_file():
            files.append(path)
    scripts = edge_root / "scripts"
    for name in sorted(_ALLOWED_SCRIPT_FILES):
        path = scripts / name
        if path.is_file():
            files.append(path)
    wheelhouse = edge_root / "wheelhouse"
    if wheelhouse.is_dir():
        files.extend(sorted(path for path in wheelhouse.glob("*.whl") if path.is_file()))
    return sorted(set(files), key=lambda item: item.as_posix())


def _assert_runtime_bundle(files: list[Path], edge_root: Path) -> None:
    relative = {path.relative_to(edge_root).as_posix() for path in files}
    required = {"requirements.runtime.txt", "requirements.runtime.lock"}
    missing = sorted(required - relative)
    wheels = [name for name in relative if name.startswith("wheelhouse/") and name.endswith(".whl")]
    if missing or not wheels:
        raise RuntimeError(
            "Artefact P9 incomplet : "
            + (f"fichiers manquants {', '.join(missing)}; " if missing else "")
            + ("wheelhouse vide" if not wheels else "")
        )


def build_release_artifact(edge_root: Path, output_dir: Path, version: str) -> dict[str, object]:
    if not _VERSION_RE.fullmatch(version):
        raise ValueError("Version Edge invalide : format attendu edge-agent-X.Y.Z")
    edge_root = edge_root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{version}.tar.gz"
    files = _included_files(edge_root)
    if not files:
        raise RuntimeError("Aucun fichier Edge à empaqueter")
    _assert_runtime_bundle(files, edge_root)

    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for path in files:
                    relative = path.relative_to(edge_root.parent)
                    info = tar.gettarinfo(str(path), arcname=relative.as_posix())
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.mode = 0o755 if path.parent.name == "scripts" else 0o644
                    with path.open("rb") as handle:
                        tar.addfile(info, handle)

    digest = hashlib.sha256()
    size = 0
    with output.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    result = {
        "software_version": version,
        "artifact_path": str(output.resolve()),
        "artifact_sha256": digest.hexdigest(),
        "artifact_size_bytes": size,
        "file_count": len(files),
        "runtime_wheels": sum(1 for path in files if path.parent.name == "wheelhouse"),
    }
    (output_dir / f"{version}.manifest-input.json").write_text(
        json.dumps(result, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Construit un artefact Center Edge P9 déterministe et autonome.")
    parser.add_argument("--version", required=True, help="Exemple : edge-agent-0.4.0")
    parser.add_argument("--edge-root", default="edge_agent")
    parser.add_argument("--output-dir", default="dist/edge-releases")
    args = parser.parse_args()
    result = build_release_artifact(Path(args.edge_root), Path(args.output_dir), args.version)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

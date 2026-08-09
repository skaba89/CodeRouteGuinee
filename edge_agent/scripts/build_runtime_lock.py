from __future__ import annotations

import argparse
import hashlib
import zipfile
from email.parser import Parser
from pathlib import Path


def _wheel_metadata(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        metadata_names = [name for name in archive.namelist() if name.endswith('.dist-info/METADATA')]
        if len(metadata_names) != 1:
            raise RuntimeError(f"Wheel invalide ou ambigu : {path.name}")
        metadata = Parser().parsestr(archive.read(metadata_names[0]).decode('utf-8', errors='strict'))
    name = str(metadata.get('Name') or '').strip()
    version = str(metadata.get('Version') or '').strip()
    if not name or not version:
        raise RuntimeError(f"Métadonnées Name/Version absentes : {path.name}")
    return name, version


def build_hash_lock(wheelhouse: Path, output: Path) -> list[str]:
    wheels = sorted(wheelhouse.glob('*.whl'))
    if not wheels:
        raise RuntimeError('Wheelhouse vide : aucune dépendance runtime à verrouiller')

    grouped: dict[tuple[str, str], list[str]] = {}
    for wheel in wheels:
        name, version = _wheel_metadata(wheel)
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        grouped.setdefault((name, version), []).append(digest)

    lines: list[str] = []
    for (name, version), hashes in sorted(grouped.items(), key=lambda item: item[0][0].lower()):
        suffix = ''.join(f' --hash=sha256:{digest}' for digest in sorted(set(hashes)))
        lines.append(f'{name}=={version}{suffix}')
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description='Génère requirements.runtime.lock depuis un wheelhouse vérifié.')
    parser.add_argument('--wheelhouse', default='edge_agent/wheelhouse')
    parser.add_argument('--output', default='edge_agent/requirements.runtime.lock')
    args = parser.parse_args()
    lines = build_hash_lock(Path(args.wheelhouse), Path(args.output))
    print(f'{len(lines)} dépendances runtime verrouillées avec SHA-256.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

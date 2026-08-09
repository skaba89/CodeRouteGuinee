from __future__ import annotations

import hashlib
import importlib.util
import zipfile
from pathlib import Path


def _load_builder():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_runtime_lock.py"
    spec = importlib.util.spec_from_file_location("coderoute_edge_runtime_lock_builder", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Impossible de charger build_runtime_lock.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_wheel(path: Path, name: str, version: str) -> None:
    dist = name.replace('-', '_')
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{dist}-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        )
        archive.writestr(f"{dist}/__init__.py", "")


def test_runtime_lock_uses_wheel_metadata_and_exact_sha256(tmp_path: Path) -> None:
    module = _load_builder()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    first = wheelhouse / "Example_Pkg-1.2.3-py3-none-any.whl"
    second = wheelhouse / "dependency-4.5.6-py3-none-any.whl"
    _fake_wheel(first, "Example-Pkg", "1.2.3")
    _fake_wheel(second, "dependency", "4.5.6")
    output = tmp_path / "requirements.runtime.lock"

    lines = module.build_hash_lock(wheelhouse, output)
    text = output.read_text(encoding="utf-8")
    assert lines == text.strip().splitlines()
    assert f"Example-Pkg==1.2.3 --hash=sha256:{hashlib.sha256(first.read_bytes()).hexdigest()}" in text
    assert f"dependency==4.5.6 --hash=sha256:{hashlib.sha256(second.read_bytes()).hexdigest()}" in text


def test_runtime_lock_rejects_empty_wheelhouse(tmp_path: Path) -> None:
    module = _load_builder()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    try:
        module.build_hash_lock(wheelhouse, tmp_path / "lock")
    except RuntimeError as exc:
        assert "Wheelhouse vide" in str(exc)
    else:
        raise AssertionError("Un wheelhouse vide doit être refusé")

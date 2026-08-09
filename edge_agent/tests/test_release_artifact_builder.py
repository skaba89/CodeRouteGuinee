from __future__ import annotations

import importlib.util
import tarfile
from pathlib import Path


def _load_builder():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_release_artifact.py"
    spec = importlib.util.spec_from_file_location("coderoute_edge_release_builder", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Impossible de charger le builder de release Edge")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_builder_is_deterministic_and_excludes_local_secrets(tmp_path: Path) -> None:
    module = _load_builder()
    edge = tmp_path / "edge_agent"
    package = edge / "coderoute_edge"
    scripts = edge / "scripts"
    tests = edge / "tests"
    package.mkdir(parents=True)
    scripts.mkdir()
    tests.mkdir()
    (package / "__init__.py").write_text("__version__='0.3.1'\n", encoding="utf-8")
    (package / "app.py").write_text("# app\n", encoding="utf-8")
    (edge / "requirements.txt").write_text("fastapi==0.115.6\n", encoding="utf-8")
    (scripts / "apply_verified_release.py").write_text("# updater\n", encoding="utf-8")
    (tests / "test_secret.py").write_text("SHOULD_NOT_SHIP=True\n", encoding="utf-8")
    secret_dir = edge / ".coderoute-edge"
    secret_dir.mkdir()
    (secret_dir / "private-key.pem").write_text("PRIVATE SECRET", encoding="utf-8")

    version = "edge-agent-0.3.1"
    first = module.build_release_artifact(edge, tmp_path / "out1", version)
    second = module.build_release_artifact(edge, tmp_path / "out2", version)
    assert first["software_version"] == version
    assert Path(first["artifact_path"]).name == f"{version}.tar.gz"
    assert first["artifact_sha256"] == second["artifact_sha256"]
    assert first["artifact_size_bytes"] == second["artifact_size_bytes"]

    with tarfile.open(first["artifact_path"], "r:gz") as archive:
        names = archive.getnames()
    assert "edge_agent/coderoute_edge/__init__.py" in names
    assert "edge_agent/requirements.txt" in names
    assert "edge_agent/scripts/apply_verified_release.py" in names
    assert all("tests/" not in name for name in names)
    assert all("private-key" not in name for name in names)

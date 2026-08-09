from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def _load_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_system_update.py"
    spec = importlib.util.spec_from_file_location("coderoute_edge_run_system_update", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Impossible de charger run_system_update.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response: FakeResponse, **_kwargs):
        self.response = response
        self.last_url = None
        self.last_headers = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, url: str, headers: dict):
        self.last_url = url
        self.last_headers = headers
        return self.response


def _staged(root: Path) -> dict:
    root.mkdir(parents=True)
    payload = {
        "release_id": "rel-p9-refresh",
        "action": "install",
        "source_release_id": None,
        "software_version": "edge-agent-0.4.0",
        "artifact_sha256": "a" * 64,
        "artifact_size_bytes": 123,
        "artifact_path": str((root / "rel-p9-refresh.tar.gz").resolve()),
        "verified": True,
        "install_authorization": {"payload": {"expires_at": "old"}},
    }
    (root / "staged.json").write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _config():
    return SimpleNamespace(
        healthcheck_ca_path=None,
        public_url="https://edge-ratoma.example.test:8443",
        operator_token="operator-token-at-least-32-characters-long",
    )


def test_refresh_replaces_stale_authorization_only_for_same_release(monkeypatch, tmp_path: Path) -> None:
    module = _load_script()
    staging = tmp_path / "staging"
    _staged(staging)
    fresh = {
        "payload": {"kind": "center_edge_install_authorization_v1", "expires_at": "fresh"},
        "payload_hash": "b" * 64,
        "signature_b64": "fresh-signature",
        "signing_key_id": "edge-release-v1:fresh",
    }
    response = FakeResponse({
        "update_available": True,
        "action": "install",
        "release": {"release_id": "rel-p9-refresh", "manifest": {"release_id": "rel-p9-refresh"}},
        "install_authorization": fresh,
    })
    monkeypatch.setattr(module.httpx, "Client", lambda **kwargs: FakeClient(response, **kwargs))

    allowed, reason = module._refresh_install_authorization(_config(), staging)
    assert allowed is True and reason == "authorized"
    saved = json.loads((staging / "staged.json").read_text())
    assert saved["install_authorization"] == fresh


def test_refresh_fail_closed_when_release_is_paused_or_changed(monkeypatch, tmp_path: Path) -> None:
    module = _load_script()
    staging = tmp_path / "staging"
    original = _staged(staging)

    paused = FakeResponse({"update_available": False, "action": "none"})
    monkeypatch.setattr(module.httpx, "Client", lambda **kwargs: FakeClient(paused, **kwargs))
    allowed, reason = module._refresh_install_authorization(_config(), staging)
    assert allowed is False and reason == "release_no_longer_authorized"
    assert json.loads((staging / "staged.json").read_text())["install_authorization"] == original["install_authorization"]

    changed = FakeResponse({
        "update_available": True,
        "action": "install",
        "release": {"release_id": "another-release", "manifest": {"release_id": "another-release"}},
        "install_authorization": {"payload": {}},
    })
    monkeypatch.setattr(module.httpx, "Client", lambda **kwargs: FakeClient(changed, **kwargs))
    allowed, reason = module._refresh_install_authorization(_config(), staging)
    assert allowed is False and reason == "staged_release_not_currently_authorized"

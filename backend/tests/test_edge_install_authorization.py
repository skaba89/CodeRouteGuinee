from __future__ import annotations

import os
from datetime import UTC, datetime

from app.edge_install_authorization import EDGE_INSTALL_AUTHORIZATION_TTL_SECONDS, sign_install_authorization
from app.edge_release import release_signing_public_key_b64, verify_release_manifest


os.environ.setdefault("EDGE_RELEASE_SIGNING_SECRET", "coderoute-p9-install-auth-secret-at-least-32-characters")


def test_install_authorization_is_short_lived_signed_and_node_bound() -> None:
    now = datetime(2026, 8, 9, 6, 0, tzinfo=UTC)
    authorization = sign_install_authorization(
        release_id="rel-p9-auth",
        source_release_id=None,
        node_id="node-ratoma",
        center_id="center-ratoma",
        action="install",
        current_version="edge-agent-0.3.0",
        software_version="edge-agent-0.4.0",
        artifact_sha256="a" * 64,
        now=now,
    )
    payload = authorization["payload"]
    assert payload["node_id"] == "node-ratoma"
    assert payload["center_id"] == "center-ratoma"
    assert payload["current_version"] == "edge-agent-0.3.0"
    assert payload["software_version"] == "edge-agent-0.4.0"
    assert 300 <= EDGE_INSTALL_AUTHORIZATION_TTL_SECONDS <= 3600
    assert verify_release_manifest(
        payload,
        authorization["signature_b64"],
        release_signing_public_key_b64(),
    ) is True

    tampered = dict(payload)
    tampered["node_id"] = "node-kindia"
    assert verify_release_manifest(
        tampered,
        authorization["signature_b64"],
        release_signing_public_key_b64(),
    ) is False

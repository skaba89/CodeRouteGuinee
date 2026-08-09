from __future__ import annotations

from types import MethodType

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coderoute_edge.central import CentralClient
from coderoute_edge.crypto import b64url, sign_payload


def _public(private_key: Ed25519PrivateKey) -> str:
    return b64url(private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ))


def _client_with_keys(active: tuple[str, str], previous: tuple[str, str]) -> CentralClient:
    client = CentralClient.__new__(CentralClient)

    def keys(_self):
        return {
            "algorithm": "Ed25519",
            "key_id": active[0],
            "public_key_b64": active[1],
            "trusted_keys": [
                {"key_id": active[0], "public_key_b64": active[1], "active": True},
                {"key_id": previous[0], "public_key_b64": previous[1], "active": False},
            ],
        }

    client.release_signing_key = MethodType(keys, client)  # type: ignore[method-assign]
    return client


def test_previous_release_key_remains_valid_during_rotation() -> None:
    active_private = Ed25519PrivateKey.generate()
    previous_private = Ed25519PrivateKey.generate()
    active = ("edge-release-v1:active", _public(active_private))
    previous = ("edge-release-v1:previous", _public(previous_private))
    client = _client_with_keys(active, previous)
    manifest = {"kind": "center_edge_release_manifest_v1", "release_id": "rel-old", "software_version": "edge-agent-0.4.0"}
    bundle = {
        "manifest": manifest,
        "manifest_signature_b64": sign_payload(previous_private, manifest),
        "signing_key_id": previous[0],
    }
    assert client.verify_release_bundle(bundle) is True


def test_unknown_or_mismatched_release_key_is_rejected() -> None:
    active_private = Ed25519PrivateKey.generate()
    previous_private = Ed25519PrivateKey.generate()
    attacker_private = Ed25519PrivateKey.generate()
    active = ("edge-release-v1:active", _public(active_private))
    previous = ("edge-release-v1:previous", _public(previous_private))
    client = _client_with_keys(active, previous)
    manifest = {"kind": "center_edge_release_manifest_v1", "release_id": "rel-bad", "software_version": "edge-agent-9.9.9"}

    unknown = {
        "manifest": manifest,
        "manifest_signature_b64": sign_payload(attacker_private, manifest),
        "signing_key_id": "edge-release-v1:unknown",
    }
    assert client.verify_release_bundle(unknown) is False

    wrong_signature = {
        "manifest": manifest,
        "manifest_signature_b64": sign_payload(attacker_private, manifest),
        "signing_key_id": active[0],
    }
    assert client.verify_release_bundle(wrong_signature) is False

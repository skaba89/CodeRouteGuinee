from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_b64url(value: str) -> bytes:
    raw = (value or "").strip()
    return base64.urlsafe_b64decode(raw + ("=" * (-len(raw) % 4)))


def canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def secret_hash(value: str, *, domain: str) -> str:
    return sha256_hex((domain + "\x00" + value).encode("utf-8"))


def compare_secret(value: str, expected_hash: str, *, domain: str) -> bool:
    return hmac.compare_digest(secret_hash(value, domain=domain), expected_hash)


def load_private_key(path: Path) -> Ed25519PrivateKey:
    raw = path.read_bytes()
    key = serialization.load_pem_private_key(raw, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise RuntimeError("La clé du gateway doit être une clé privée Ed25519")
    return key


def sign_payload(private_key: Ed25519PrivateKey, payload: dict[str, Any]) -> str:
    return b64url(private_key.sign(canonical_json(payload)))


def verify_signed_payload(public_key_b64: str, payload: dict[str, Any], signature_b64: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(decode_b64url(public_key_b64)).verify(
            decode_b64url(signature_b64), canonical_json(payload)
        )
        return True
    except Exception:
        return False


def load_or_create_storage_key(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raw = path.read_bytes()
        if len(raw) != 32:
            raise RuntimeError("storage.key doit contenir exactement 32 octets")
        return raw
    raw = os.urandom(32)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)
    return raw


def encrypt_json(storage_key: bytes, payload: Any, *, aad: str) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    ciphertext = AESGCM(storage_key).encrypt(nonce, canonical_json(payload), aad.encode("utf-8"))
    return nonce, ciphertext


def decrypt_json(storage_key: bytes, nonce: bytes, ciphertext: bytes, *, aad: str) -> Any:
    raw = AESGCM(storage_key).decrypt(nonce, ciphertext, aad.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))

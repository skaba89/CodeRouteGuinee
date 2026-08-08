#!/usr/bin/env python3
"""Génère l'identité cryptographique d'un CodeRoute Center Edge Gateway.

La clé privée reste exclusivement sur le gateway du centre. Seule la clé
publique Base64URL affichée par ce script doit être transmise à la DNTT pour
l'enrôlement via POST /api/v1/center-edge/nodes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def main() -> int:
    parser = argparse.ArgumentParser(description="Générer une identité Ed25519 pour un gateway CodeRoute Edge")
    parser.add_argument("--output-dir", default=".coderoute-edge", help="Répertoire local protégé")
    parser.add_argument("--label", default="Gateway Edge Centre", help="Libellé humain du gateway")
    parser.add_argument("--force", action="store_true", help="Autoriser l'écrasement d'une identité existante")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    private_path = output_dir / "private-key.pem"
    public_path = output_dir / "public-key.txt"
    manifest_path = output_dir / "identity.json"

    if not args.force and any(path.exists() for path in (private_path, public_path, manifest_path)):
        parser.error(f"Une identité existe déjà dans {output_dir}. Utilisez --force uniquement pour une rotation volontaire.")

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(output_dir, 0o700)
    except OSError:
        pass

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_b64 = b64url(public_raw)
    fingerprint = hashlib.sha256(public_raw).hexdigest()

    private_path.write_bytes(private_pem)
    public_path.write_text(public_b64 + "\n", encoding="utf-8")
    manifest = {
        "kind": "coderoute_center_edge_identity",
        "label": args.label,
        "algorithm": "Ed25519",
        "public_key_b64": public_b64,
        "public_key_fingerprint": fingerprint,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "private_key_path": str(private_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    try:
        os.chmod(private_path, 0o600)
        os.chmod(public_path, 0o600)
        os.chmod(manifest_path, 0o600)
    except OSError:
        pass

    print("Identité CodeRoute Edge générée.")
    print(f"Répertoire         : {output_dir}")
    print(f"Fingerprint SHA256 : {fingerprint}")
    print(f"Clé publique       : {public_b64}")
    print("IMPORTANT : ne copiez jamais private-key.pem vers le serveur central ou Git.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

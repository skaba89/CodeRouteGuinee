"""
Signature d'upload Cloudinary — CodeRoute Guinée.

Flux d'upload signé :
  1. Le navigateur demande une signature au backend (endpoint /media/sign-upload)
  2. Le backend signe les paramètres avec le secret Cloudinary (jamais exposé)
  3. Le navigateur envoie le fichier DIRECTEMENT à Cloudinary avec la signature
  4. Cloudinary renvoie l'URL du média → associée à la question

Avantage : les fichiers ne transitent jamais par Render (pas de charge
serveur, pas de limite de taille Render), et le secret reste côté serveur.

La réponse inclut également la politique qualité/sécurité à appliquer AVANT
l'upload (taille, MIME, durée, résolution). Ces champs ne sont pas ajoutés aux
paramètres signés historiques afin de rester compatibles avec le frontend
actuel pendant la migration vers la Media Factory.

Docs : https://cloudinary.com/documentation/upload_images#generating_authentication_signatures
"""
from __future__ import annotations

import hashlib
import time

from app.core.config import get_settings
from app.media_policy import get_media_upload_policy


def is_configured() -> bool:
    s = get_settings()
    return bool(s.cloudinary_cloud_name and s.cloudinary_api_key and s.cloudinary_api_secret)


def build_upload_signature(resource_type: str = "image") -> dict:
    """Retourne les paramètres signés et la politique d'upload navigateur.

    `resource_type` accepte uniquement `image` ou `video`. Le dictionnaire
    `policy` est destiné à la validation côté client ; il ne fait pas partie de
    la signature Cloudinary et n'altère donc pas le flux existant.
    """
    normalized_type = (resource_type or "").strip().lower()
    policy = get_media_upload_policy(normalized_type)

    s = get_settings()
    timestamp = int(time.time())
    folder = s.cloudinary_upload_folder

    # Cloudinary : les paramètres à signer sont triés alphabétiquement,
    # concaténés en query-string, suivis du secret, puis hachés en SHA-1.
    params_to_sign = {
        "folder": folder,
        "timestamp": str(timestamp),
    }
    to_sign = "&".join(f"{k}={v}" for k, v in sorted(params_to_sign.items()))
    signature = hashlib.sha1(f"{to_sign}{s.cloudinary_api_secret}".encode()).hexdigest()

    upload_url = (
        f"https://api.cloudinary.com/v1_1/{s.cloudinary_cloud_name}/"
        f"{normalized_type}/upload"
    )

    return {
        "upload_url": upload_url,
        "api_key": s.cloudinary_api_key,
        "timestamp": timestamp,
        "folder": folder,
        "signature": signature,
        "resource_type": normalized_type,
        "policy": policy,
    }

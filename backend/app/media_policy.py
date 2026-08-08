"""Politique de sécurité et de qualité des médias CodeRoute Guinée.

Les médias d'examen sont du contenu métier sensible : ils doivent être servis
sur HTTPS, depuis une origine publique, sans possibilité de pointer vers une
adresse interne (SSRF / fuite d'infrastructure). Ce module centralise aussi les
contraintes que le frontend doit appliquer avant l'upload Cloudinary.
"""
from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit

from app.core.config import get_settings

MEDIA_TYPES = {"image", "video"}

IMAGE_UPLOAD_POLICY = {
    "resource_type": "image",
    "max_bytes": 10 * 1024 * 1024,
    "accepted_mime_types": ["image/jpeg", "image/png", "image/webp", "image/avif"],
    "recommended_min_width": 1280,
    "recommended_min_height": 720,
    "recommended_aspect_ratios": ["16:9", "4:3", "1:1"],
    "delivery_formats": ["avif", "webp", "jpeg"],
}

VIDEO_UPLOAD_POLICY = {
    "resource_type": "video",
    "max_bytes": 80 * 1024 * 1024,
    "max_duration_seconds": 30,
    "accepted_mime_types": ["video/mp4", "video/webm", "video/quicktime"],
    "recommended_min_width": 1280,
    "recommended_min_height": 720,
    "recommended_aspect_ratios": ["16:9"],
    "delivery_profiles": ["360p", "480p", "720p"],
    "adaptive_streaming": True,
    "poster_required": True,
}


def get_media_upload_policy(resource_type: str) -> dict:
    """Retourne une copie sérialisable de la politique d'upload demandée."""
    normalized = (resource_type or "").strip().lower()
    if normalized == "image":
        return dict(IMAGE_UPLOAD_POLICY)
    if normalized == "video":
        return dict(VIDEO_UPLOAD_POLICY)
    raise ValueError("resource_type doit être 'image' ou 'video'")


def _is_non_public_ip(hostname: str) -> bool:
    try:
        parsed = ip_address(hostname)
    except ValueError:
        return False
    return any((
        parsed.is_private,
        parsed.is_loopback,
        parsed.is_link_local,
        parsed.is_multicast,
        parsed.is_reserved,
        parsed.is_unspecified,
    ))


def _development_local_allowed(hostname: str, scheme: str) -> bool:
    settings = get_settings()
    if settings.environment.lower() == "production":
        return False
    return scheme == "http" and hostname in {"localhost", "127.0.0.1", "::1"}


def validate_media_url(value: str, resource_type: str) -> str:
    """Valide et normalise une URL finale de média.

    Principes :
    - HTTPS obligatoire hors localhost de développement ;
    - pas d'identifiants embarqués dans l'URL ;
    - pas d'IP privées/loopback/link-local en production ;
    - pas de noms d'hôtes internes évidents ;
    - cohérence `image`/`video` pour une URL Cloudinary standard ;
    - si Cloudinary est configuré, une URL `res.cloudinary.com` doit appartenir
      au cloud du projet et non à un autre compte.
    """
    normalized_type = (resource_type or "").strip().lower()
    if normalized_type not in MEDIA_TYPES:
        raise ValueError("Le type de média doit être 'image' ou 'video'.")

    normalized = (value or "").strip()
    if not normalized:
        raise ValueError("L'URL du média est vide.")

    parsed = urlsplit(normalized)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    scheme = parsed.scheme.lower()

    if not hostname:
        raise ValueError("L'URL du média doit contenir un nom d'hôte valide.")
    if parsed.username or parsed.password:
        raise ValueError("Les identifiants intégrés dans une URL média sont interdits.")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Le port indiqué dans l'URL média est invalide.") from exc

    if scheme != "https":
        if not _development_local_allowed(hostname, scheme):
            raise ValueError("Les médias doivent être servis en HTTPS.")

    if not _development_local_allowed(hostname, scheme):
        if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
            raise ValueError("Une URL média ne peut pas cibler un hôte interne.")
        if _is_non_public_ip(hostname):
            raise ValueError("Une URL média ne peut pas cibler une adresse IP privée ou non publique.")
        if "." not in hostname:
            raise ValueError("Le nom d'hôte du média doit être public et pleinement qualifié.")
        if port not in (None, 443):
            raise ValueError("Un média HTTPS de production doit utiliser le port standard 443.")

    # L'API d'upload n'est jamais une URL de livraison à persister dans Question.
    if hostname == "api.cloudinary.com":
        raise ValueError("L'URL d'upload Cloudinary ne peut pas être utilisée comme URL de média final.")

    if hostname == "res.cloudinary.com":
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 4 or path_parts[2] != "upload":
            raise ValueError("L'URL Cloudinary de livraison est malformée.")

        cloud_name, cloud_resource_type = path_parts[0], path_parts[1]
        if cloud_resource_type not in MEDIA_TYPES:
            raise ValueError("Le type de ressource Cloudinary est invalide.")
        if cloud_resource_type != normalized_type:
            raise ValueError("Le type déclaré du média ne correspond pas à l'URL Cloudinary.")

        settings = get_settings()
        if settings.cloudinary_cloud_name and cloud_name != settings.cloudinary_cloud_name:
            raise ValueError("Le média Cloudinary appartient à un autre compte que celui de CodeRoute.")

    return normalized

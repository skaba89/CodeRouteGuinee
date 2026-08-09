from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EdgeAgentConfig:
    central_url: str
    node_id: str
    center_id: str
    private_key_path: Path
    database_path: Path
    storage_key_path: Path
    media_cache_dir: Path
    operator_token: str
    allowed_origins: tuple[str, ...]
    release_dir: Path = Path(".coderoute-edge/releases")
    software_version: str = "edge-agent-0.4.0"
    max_media_bytes: int = 50 * 1024 * 1024
    max_release_bytes: int = 512 * 1024 * 1024
    bind_host: str = "0.0.0.0"
    bind_port: int = 8443
    public_url: str = ""
    tls_cert_path: Path | None = None
    tls_key_path: Path | None = None
    allow_insecure_http: bool = False
    maintenance_windows: str = "sun@01:00-04:00"
    maintenance_timezone: str = "Africa/Conakry"
    systemd_service_name: str = "coderoute-edge.service"
    healthcheck_timeout_seconds: int = 60
    healthcheck_ca_path: Path | None = None

    @classmethod
    def from_env(cls) -> "EdgeAgentConfig":
        central_url = os.environ.get("CODEROUTE_EDGE_CENTRAL_URL", "").strip().rstrip("/")
        node_id = os.environ.get("CODEROUTE_EDGE_NODE_ID", "").strip()
        center_id = os.environ.get("CODEROUTE_EDGE_CENTER_ID", "").strip()
        private_key_path = Path(os.environ.get("CODEROUTE_EDGE_PRIVATE_KEY_PATH", ".coderoute-edge/private-key.pem"))
        database_path = Path(os.environ.get("CODEROUTE_EDGE_DB_PATH", ".coderoute-edge/edge.db"))
        storage_key_path = Path(os.environ.get("CODEROUTE_EDGE_STORAGE_KEY_PATH", ".coderoute-edge/storage.key"))
        media_cache_dir = Path(os.environ.get("CODEROUTE_EDGE_MEDIA_DIR", ".coderoute-edge/media"))
        release_dir = Path(os.environ.get("CODEROUTE_EDGE_RELEASE_DIR", ".coderoute-edge/releases"))
        operator_token = os.environ.get("CODEROUTE_EDGE_OPERATOR_TOKEN", "").strip()
        origins = tuple(
            origin.strip()
            for origin in os.environ.get(
                "CODEROUTE_EDGE_ALLOWED_ORIGINS",
                "https://coderouteguinee-frontend.onrender.com",
            ).split(",")
            if origin.strip()
        )
        version = os.environ.get("CODEROUTE_EDGE_SOFTWARE_VERSION", "edge-agent-0.4.0").strip()
        max_media = int(os.environ.get("CODEROUTE_EDGE_MAX_MEDIA_BYTES", str(50 * 1024 * 1024)))
        max_release = int(os.environ.get("CODEROUTE_EDGE_MAX_RELEASE_BYTES", str(512 * 1024 * 1024)))
        bind_host = os.environ.get("CODEROUTE_EDGE_BIND_HOST", "0.0.0.0").strip()
        bind_port = int(os.environ.get("CODEROUTE_EDGE_BIND_PORT", "8443"))
        public_url = os.environ.get("CODEROUTE_EDGE_PUBLIC_URL", "").strip().rstrip("/")
        cert_raw = os.environ.get("CODEROUTE_EDGE_TLS_CERT_PATH", "").strip()
        key_raw = os.environ.get("CODEROUTE_EDGE_TLS_KEY_PATH", "").strip()
        tls_cert = Path(cert_raw) if cert_raw else None
        tls_key = Path(key_raw) if key_raw else None
        insecure = _truthy(os.environ.get("CODEROUTE_EDGE_ALLOW_INSECURE_HTTP"))
        maintenance_windows = os.environ.get("CODEROUTE_EDGE_MAINTENANCE_WINDOWS", "sun@01:00-04:00").strip()
        maintenance_timezone = os.environ.get("CODEROUTE_EDGE_MAINTENANCE_TIMEZONE", "Africa/Conakry").strip()
        systemd_service_name = os.environ.get("CODEROUTE_EDGE_SYSTEMD_SERVICE", "coderoute-edge.service").strip()
        healthcheck_timeout = int(os.environ.get("CODEROUTE_EDGE_HEALTHCHECK_TIMEOUT_SECONDS", "60"))
        ca_raw = os.environ.get("CODEROUTE_EDGE_HEALTHCHECK_CA_PATH", "").strip()
        healthcheck_ca = Path(ca_raw) if ca_raw else None

        errors: list[str] = []
        if not central_url.startswith("https://"):
            errors.append("CODEROUTE_EDGE_CENTRAL_URL doit utiliser HTTPS")
        if not node_id:
            errors.append("CODEROUTE_EDGE_NODE_ID est obligatoire")
        if not center_id:
            errors.append("CODEROUTE_EDGE_CENTER_ID est obligatoire")
        if len(operator_token) < 32:
            errors.append("CODEROUTE_EDGE_OPERATOR_TOKEN doit contenir au moins 32 caractères")
        if not origins or any(origin == "*" for origin in origins):
            errors.append("CODEROUTE_EDGE_ALLOWED_ORIGINS doit être une liste explicite sans wildcard")
        if max_media < 1024 * 1024:
            errors.append("CODEROUTE_EDGE_MAX_MEDIA_BYTES est trop faible")
        if max_release < 1024 * 1024:
            errors.append("CODEROUTE_EDGE_MAX_RELEASE_BYTES est trop faible")
        if bind_port < 1 or bind_port > 65535:
            errors.append("CODEROUTE_EDGE_BIND_PORT invalide")
        if not public_url:
            errors.append("CODEROUTE_EDGE_PUBLIC_URL est obligatoire pour générer les URLs média LAN")
        elif not insecure and not public_url.startswith("https://"):
            errors.append("CODEROUTE_EDGE_PUBLIC_URL doit utiliser HTTPS en centre")
        if not insecure and (tls_cert is None or tls_key is None):
            errors.append(
                "TLS LAN obligatoire : définir CODEROUTE_EDGE_TLS_CERT_PATH et CODEROUTE_EDGE_TLS_KEY_PATH "
                "(ou CODEROUTE_EDGE_ALLOW_INSECURE_HTTP=true uniquement en développement)"
            )
        if not maintenance_windows:
            errors.append("CODEROUTE_EDGE_MAINTENANCE_WINDOWS ne peut pas être vide")
        if not maintenance_timezone:
            errors.append("CODEROUTE_EDGE_MAINTENANCE_TIMEZONE ne peut pas être vide")
        if not systemd_service_name or "/" in systemd_service_name:
            errors.append("CODEROUTE_EDGE_SYSTEMD_SERVICE invalide")
        if healthcheck_timeout < 10 or healthcheck_timeout > 600:
            errors.append("CODEROUTE_EDGE_HEALTHCHECK_TIMEOUT_SECONDS doit être compris entre 10 et 600")
        if errors:
            raise RuntimeError("Configuration Edge invalide : " + "; ".join(errors))

        return cls(
            central_url=central_url,
            node_id=node_id,
            center_id=center_id,
            private_key_path=private_key_path,
            database_path=database_path,
            storage_key_path=storage_key_path,
            media_cache_dir=media_cache_dir,
            operator_token=operator_token,
            allowed_origins=origins,
            release_dir=release_dir,
            software_version=version,
            max_media_bytes=max_media,
            max_release_bytes=max_release,
            bind_host=bind_host,
            bind_port=bind_port,
            public_url=public_url,
            tls_cert_path=tls_cert,
            tls_key_path=tls_key,
            allow_insecure_http=insecure,
            maintenance_windows=maintenance_windows,
            maintenance_timezone=maintenance_timezone,
            systemd_service_name=systemd_service_name,
            healthcheck_timeout_seconds=healthcheck_timeout,
            healthcheck_ca_path=healthcheck_ca,
        )

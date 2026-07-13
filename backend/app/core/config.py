"""
Configuration CodeRoute Guinée — chargée depuis les variables d'environnement.
Aucun secret réel ne doit figurer dans ce fichier.
"""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── JWT / Sécurité ────────────────────────────────────────────────────
    secret_key: str = "CHANGE_ME_secret_key_must_be_set_in_env"
    csrf_secret: str = "CHANGE_ME_csrf_secret_must_be_set_in_env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    admin_registration_token: str | None = None

    # ── Base de données ───────────────────────────────────────────────────
    database_url: str = "CHANGE_ME_database_url_must_be_set_in_env"
    auto_create_tables: bool = True   # False en production (Alembic gère le schéma)

    # ── Application ───────────────────────────────────────────────────────
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    enable_api_docs: bool = True

    # ── Email (Brevo) ─────────────────────────────────────────────────────
    brevo_api_key: str = ""
    email_from: str = "noreply@coderoute.gov.gn"
    email_from_name: str = "CodeRoute Guinée — DNTT"

    # ── Hébergement média (Cloudinary) ────────────────────────────────────
    # Upload signé : le navigateur envoie directement à Cloudinary, le
    # serveur ne fait que signer la requête (les fichiers ne transitent
    # pas par Render). Vide = fonction upload désactivée proprement.
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_upload_folder: str = "coderoute/questions"

    # ── Bootstrap admin ───────────────────────────────────────────────────
    bootstrap_admin_email: str = "super_admin@coderoute.gov.gn"
    bootstrap_admin_password: str = ""        # vide = pas de seed auto
    bootstrap_admin_name: str = "Directeur National CodeRoute"

    # ── Mobile Money ──────────────────────────────────────────────────────
    mobile_money_mode: str = "sandbox"
    orange_money_api_key: str = ""
    orange_money_merchant_id: str = ""
    mtn_momo_api_key: str = ""
    mtn_momo_subscription_key: str = ""
    wave_api_key: str = ""

    # ── Monitoring ────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.05
    app_version: str = "0.14.0"

    # ── DB Pool ───────────────────────────────────────────────────────────
    db_pool_size: int = 2
    db_max_overflow: int = 3
    db_pool_timeout: int = 30
    db_pool_recycle: int = 60

    # ── Auth / Rate limiting ─────────────────────────────────────────────
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    bootstrap_admin_full_name: str = ""   # alias de bootstrap_admin_name

    # ── API ─────────────────────────────────────────────────────────────
    api_v1_prefix: str = "/api/v1"
    project_name: str = "CodeRoute Guinée"
    sentry_environment: str = ""   # auto-set via property si vide
    sentry_sample_rate: float = 0.05

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # ── Propriétés calculées ──────────────────────────────────────────────
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def validate_production_secrets(self) -> None:
        """Refuse de démarrer en production avec des secrets absents, factices ou faibles."""
        if not self.is_production:
            return

        # Sous-chaînes interdites (jamais présentes dans un vrai secret/URL)
        PLACEHOLDER_SUBSTRINGS = ("CHANGE_ME", "change-me-in-production", "changeme")

        # Secrets notoirement faibles : un secret peut ne pas être un
        # placeholder tout en étant trivialement devinable. Un audit de
        # sécurité externe (exigé pour un déploiement national) le relèverait.
        WEAK_VALUES = {
            "secret", "password", "passwd", "admin", "test", "dev", "default",
            "secretkey", "secret_key", "mysecret", "coderoute", "guinee",
            "123456", "12345678", "password123", "azerty", "qwerty",
        }
        MIN_SECRET_LENGTH = 32  # 256 bits en hexadécimal

        errors: list[str] = []

        def _is_placeholder(v: str, name: str) -> None:
            if not v or not v.strip() or any(p in v for p in PLACEHOLDER_SUBSTRINGS):
                errors.append(f"{name} est vide ou placeholder — définir dans Render Dashboard")

        def _check_strength(v: str, name: str) -> None:
            """Un secret de production doit être long et non devinable."""
            if not v or not v.strip():
                return  # déjà signalé par _is_placeholder
            if len(v) < MIN_SECRET_LENGTH:
                errors.append(
                    f"{name} est trop court ({len(v)} caractères, minimum "
                    f"{MIN_SECRET_LENGTH}) — générer avec : openssl rand -hex 32"
                )
            if v.strip().lower() in WEAK_VALUES:
                errors.append(f"{name} est une valeur faible et devinable — générer un secret aléatoire")
            if len(set(v)) < 8:
                errors.append(f"{name} a trop peu de caractères distincts — générer un secret aléatoire")

        _is_placeholder(self.secret_key,   "SECRET_KEY")
        _is_placeholder(self.csrf_secret,  "CSRF_SECRET")
        _is_placeholder(self.database_url, "DATABASE_URL")

        _check_strength(self.secret_key,  "SECRET_KEY")
        _check_strength(self.csrf_secret, "CSRF_SECRET")

        # SECRET_KEY et CSRF_SECRET doivent être DISTINCTS : réutiliser le même
        # secret pour deux usages cryptographiques est une faute classique.
        if self.secret_key and self.secret_key == self.csrf_secret:
            errors.append("SECRET_KEY et CSRF_SECRET doivent être différents")

        if self.enable_api_docs:
            errors.append("ENABLE_API_DOCS doit être false en production")

        if any("localhost" in o or "127.0.0.1" in o for o in self.cors_origin_list):
            errors.append("CORS_ORIGINS ne doit pas contenir localhost en production")

        local_hosts = {"localhost", "127.0.0.1", "testserver"}
        if any(h in local_hosts for h in self.allowed_host_list):
            errors.append("ALLOWED_HOSTS ne doit pas contenir localhost/testserver en production")

        # La base de production ne doit pas être un SQLite local (perte de
        # données garantie sur un hébergement éphémère).
        if self.database_url and self.database_url.strip().startswith("sqlite"):
            errors.append("DATABASE_URL ne doit pas être SQLite en production — utiliser PostgreSQL")

        if errors:
            msg = "\n".join(f"  ❌ {e}" for e in errors)
            raise RuntimeError(
                f"Configuration de production invalide :\n{msg}\n"
                "Configurer ces variables dans Render Dashboard et redéployer."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

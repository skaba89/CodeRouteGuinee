from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name: str = "CodeRoute Guinee API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"
    admin_registration_token: str | None = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    database_url: str = "sqlite:///./coderoute.db"
    auto_create_tables: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    enable_api_docs: bool = True
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_full_name: str = "Administrateur National CodeRoute"
    # Monitoring Sentry
    sentry_dsn: str = ""
    sentry_environment: str = ""
    sentry_sample_rate: float = 0.2

    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    # Mobile Money
    mobile_money_mode: str = "sandbox"
    orange_money_client_id: str = ""
    orange_money_client_secret: str = ""
    orange_money_merchant_code: str = ""
    orange_money_base_url: str = "https://api.orange.com"
    mtn_money_subscription_key: str = ""
    mtn_money_api_user_id: str = ""
    mtn_money_api_key: str = ""
    mtn_money_environment: str = "sandbox"
    mtn_money_base_url: str = "https://sandbox.momodeveloper.mtn.com"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# There is ONE .env for the whole project — at the repo root. The backend is usually launched from
# backend/ (`cd backend && uvicorn app.main:app`), so a CWD-relative ".env" wouldn't be found; we
# resolve the repo-root .env by absolute path (this file is backend/app/core/config.py, so the repo
# root is parents[3]). Missing file is ignored by pydantic; in Docker, real env vars are injected
# and take precedence. (No separate backend/.env — keep everything in the single root .env.)
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT_ENV),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "TimeSense"
    app_env: Literal["development", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = "change_me"

    # Database
    database_url: str = "postgresql+asyncpg://timesense:timesense@localhost:5432/timesense"
    database_url_sync: str = "postgresql://timesense:timesense@localhost:5432/timesense"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Firebase
    firebase_project_id: str = ""
    firebase_service_account_json: str = "{}"

    # Everyone gets Premium free for their first N days (intro trial), no payment required.
    intro_trial_days: int = 14

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_monthly: str = ""
    stripe_price_annual: str = ""
    stripe_price_founder: str = ""

    # Apple
    apple_bundle_id: str = "com.timesense.app"
    apple_team_id: str = ""
    apple_app_store_connect_key_id: str = ""
    apple_app_store_connect_issuer_id: str = ""
    apple_app_store_connect_private_key: str = ""

    # Google Play
    google_play_package_name: str = "com.timesense.app"
    google_play_service_account_json: str = "{}"

    # APNs (Apple Push Notification service). Token-based (JWT) auth. Empty key → push disabled.
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_private_key: str = ""          # contents of the .p8 (PEM), or with literal \n escapes
    apns_bundle_id: str = "com.timesense.app"
    apns_use_sandbox: bool = True       # sandbox for dev/TestFlight; set False for production

    # Maps (server-side geocoding / places / travel time). Empty → NullMapsProvider (location
    # candidates stay low-confidence and never invent distances).
    google_maps_api_key: str = ""

    # LLM
    openai_api_key: str = ""
    llm_default_provider: str = "openai"
    llm_default_model: str = "gpt-4o"

    # OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/integrations/google/callback"
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_redirect_uri: str = "http://localhost:8000/api/v1/integrations/microsoft/callback"
    # Where the /callback deep-links back to once tokens are stored (mobile app / web companion).
    oauth_success_redirect: str = "timesense://integrations/connected"
    oauth_failure_redirect: str = "timesense://integrations/failed"

    # Slack
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_signing_secret: str = ""

    # Todoist
    todoist_client_id: str = ""
    todoist_client_secret: str = ""

    # Notion
    notion_client_id: str = ""
    notion_client_secret: str = ""

    # Monitoring (Sentry-optional; empty DSN => disabled)
    sentry_dsn: str = ""

    # Security hardening
    # Fernet key for encrypting integration OAuth tokens at rest. If empty, a key is derived
    # deterministically from secret_key (fine for dev; set a real key in production).
    token_encryption_key: str = ""
    rate_limit_capture_per_minute: int = 30
    rate_limit_account_delete_per_hour: int = 5
    notion_version: str = "2022-06-28"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

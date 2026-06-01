"""Uygulama ayarlari - ortam degiskenlerinden okunur (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Genel
    environment: str = "development"
    debug: bool = True
    project_name: str = "Argus Intelligence"

    # Veritabani
    database_url: str = "postgresql+asyncpg://argus:argus_dev_password@postgres:5432/argus"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # JWT
    jwt_secret: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    # Claude / Anthropic
    anthropic_api_key: str = ""
    claude_triage_model: str = "claude-haiku-4-5"
    claude_summary_model: str = "claude-sonnet-4-6"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_enabled: bool = False

    # SMTP / bildirim
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@argus.local"

    # CORS - frontend kaynagi
    frontend_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

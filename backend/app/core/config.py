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
    # Zamanlanmis tarama dispatcher'inin (Celery beat) calisma sikligi (saniye)
    scan_beat_interval_seconds: int = 60
    # Zamanlanmis rapor dispatcher'inin calisma sikligi (saniye; varsayilan saatlik)
    report_beat_interval_seconds: int = 3600

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
    # Plan kademesi basina Stripe Price ID'leri (checkout icin)
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_enterprise: str = ""

    # OSINT feed API anahtarlari (bos ise ilgili konnektor demo/atlanir)
    hibp_api_key: str = ""  # HaveIBeenPwned (darkweb) - GERCEK baglandi
    shodan_api_key: str = ""  # Shodan (security_scan) - GERCEK baglandi
    # Marka koruma: gercek DNS-over-HTTPS dogrulamasi (anahtarsiz; bayrakla acilir)
    brand_dns_check: bool = False
    # Diger modullerin gercek kaynak anahtarlari (saglayici sozlesmesi gerektirir;
    # bos ise demo konnektore dusulur). Entegrasyon noktalari konnektor stub'larinda.
    brand_feed_api_key: str = ""  # brand_protection (yeni kayit/WHOIS feed)
    search_api_key: str = ""  # illegal_site (arama/domain feed)
    chain_analysis_api_key: str = ""  # financial_crime (zincir analizi/yaptirim)
    scrape_api_key: str = ""  # competitor_intel (web kazima/fiyat)
    social_api_key: str = ""  # disinformation (sosyal medya/anlati)
    court_records_api_key: str = ""  # due_diligence (OpenCorporates api_token)
    ai_probe_api_key: str = ""  # ai_testing (uc nokta icin opsiyonel Bearer token)
    # ai_testing: gercek izinli red-team probe'lari (musterinin KENDI uc noktasina)
    ai_live_probe: bool = False
    # illegal_site: Google Programmable Search (CSE) - arama motoru id'si
    google_cse_id: str = ""
    # disinformation: Google News RSS (anahtarsiz medya-mention izleme; true=ac)
    disinfo_news: bool = False
    # competitor_intel: rakip ana sayfasi izleme (anahtarsiz; true=ac)
    competitor_web_watch: bool = False
    # social_media: sosyal medya hesap arama API'si (saglayici sozlesmesi; bos=demo)
    social_search_api_key: str = ""

    # Bildirim esigi: bu onem seviyesi ve uzerindeki YENI bulgularda bildirim gonderilir
    # (info|low|medium|high|critical). Periyodik taramalarda tekrar eden bulgular bildirilmez.
    notify_min_severity: str = "info"

    # SMTP / bildirim
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@argus.local"

    # CORS - frontend kaynagi
    frontend_origin: str = "http://localhost:3000"
    # Auth uclari icin IP basina dakikalik istek limiti (brute-force korumasi)
    auth_rate_limit_per_minute: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

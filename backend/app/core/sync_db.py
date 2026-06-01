"""Senkron SQLAlchemy oturumu - Celery worker icin (async motor loop'a baglidir).

API tarafi async (asyncpg) kullanir; Celery gorevleri ise bu senkron motoru (psycopg)
kullanir. Boylece event loop catismalari olmaz.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# postgresql+asyncpg://...  ->  postgresql+psycopg://...
_sync_url = settings.database_url.replace("+asyncpg", "+psycopg")

sync_engine = create_engine(_sync_url, pool_pre_ping=True, future=True)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False, class_=Session)

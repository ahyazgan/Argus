"""Async SQLAlchemy motoru, oturum ve ortak Base sinifi."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Tum modeller bu Base'i paylasir."""


class TimestampMixin:
    """Olusturma/guncelleme zaman damgalari."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    """UUID birincil anahtar sutunu uretir."""
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI bagimliligi: istek basina veritabani oturumu."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

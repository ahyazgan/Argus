"""Argus Intelligence - FastAPI uygulama giris noktasi."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.middleware import AuthRateLimitMiddleware, SecurityHeadersMiddleware
from app.modules import load_modules

# Tum modellerin Base.metadata'ya kaydolmasi icin ice aktar (create_all icin gerekli)
import app.models  # noqa: E402, F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tum modulleri kayit defterine yukle (modules/<ad>/module.py kendini kaydeder)
    load_modules()
    # MVP: tablolari acilista olustur (idempotent). Uretimde Alembic kullanin.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="Tek platform - sonsuz modul - bir abonelik. OSINT & tehdit istihbarati.",
    lifespan=lifespan,
)

# Guvenlik basliklari (tum yanitlara) + auth uclari icin rate limit
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    AuthRateLimitMiddleware,
    limit_per_minute=settings.auth_rate_limit_per_minute,
    protected_prefixes=(
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/accept-invite",
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": settings.project_name, "docs": "/docs", "api": "/api/v1"}

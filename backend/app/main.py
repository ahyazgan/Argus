"""Argus Intelligence - FastAPI uygulama giris noktasi."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": settings.project_name, "docs": "/docs", "api": "/api/v1"}

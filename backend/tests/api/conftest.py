"""DB'li API testleri icin fikstur'lar.

Gercek bir PostgreSQL gerektirir. `DATABASE_URL` ortam degiskeni tanimli degilse bu
testler ATLANIR (CI'da bir postgres servisi ile calistirilir; yerelde de bir test
veritabani vererek calistirilabilir). Tablolar create_all ile kurulur.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio

@pytest_asyncio.fixture
async def client():
    # DATABASE_URL yoksa DB'li API testlerini atla (CI'da postgres servisi ile calisir)
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL tanimli degil (DB'li API testleri)")

    # Geç import: engine baglantisi yalnizca DB varken kurulur
    from httpx import ASGITransport, AsyncClient

    from app.core.database import Base, engine
    from app.main import app
    from app.modules import load_modules

    load_modules()
    async with engine.begin() as conn:
        # Temiz sema (her oturumda yeniden kur)
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await engine.dispose()

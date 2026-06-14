"""API anahtari yonetimi - programatik REST erisimi icin tenant kapsamli anahtarlar.

Olusturma/iptal yalnizca OWNER/ADMIN icindir. Ham anahtar yalnizca olusturuldugu
yanitla bir kez doner; sonra yalnizca onek + son kullanim gosterilir.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_tenant_id, require_role
from app.core.security import generate_api_key
from app.core_services.audit import record_audit
from app.models.api_key import ApiKey
from app.models.user import User, UserRole

router = APIRouter()


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ApiKeyCreated(ApiKeyOut):
    # Ham anahtar - yalnizca olusturmada bir kez doner
    key: str


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.organization_id == tenant_id)
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    payload: ApiKeyCreate,
    user: User = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    raw, prefix, hashed = generate_api_key()
    rec = ApiKey(
        organization_id=tenant_id,
        name=payload.name.strip(),
        prefix=prefix,
        hashed_key=hashed,
        created_by=user.id,
    )
    db.add(rec)
    record_audit(
        db,
        organization_id=tenant_id,
        user_id=user.id,
        action="api_key.create",
        target_type="api_key",
        target_id=str(rec.id),
        detail=payload.name.strip(),
    )
    await db.flush()
    await db.refresh(rec)
    return ApiKeyCreated(key=raw, **ApiKeyOut.model_validate(rec).model_dump())


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    rec = (
        await db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.organization_id == tenant_id)
        )
    ).scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="API anahtari bulunamadi")
    if rec.revoked_at is None:
        rec.revoked_at = datetime.now(timezone.utc)
        record_audit(
            db,
            organization_id=tenant_id,
            user_id=user.id,
            action="api_key.revoke",
            target_type="api_key",
            target_id=str(rec.id),
            detail=rec.name,
        )
    await db.flush()

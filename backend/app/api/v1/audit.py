"""Denetim gunlugu uclari - kurum icindeki onemli degisikliklerin listesi."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.models.audit import AuditLog
from app.models.user import User, UserRole

router = APIRouter()


class AuditOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AuditOut])
async def list_audit(
    manager: User = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, le=500),
) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == manager.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

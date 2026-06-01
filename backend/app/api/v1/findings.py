"""Bulgu (Finding) uclari: listeleme, detay, durum guncelleme."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_tenant_id
from app.models.finding import Finding, FindingStatus
from app.schemas.monitor import FindingOut

router = APIRouter()


@router.get("", response_model=list[FindingOut])
async def list_findings(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    monitor_id: uuid.UUID | None = Query(default=None),
    module: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, le=500),
) -> list[Finding]:
    stmt = select(Finding).where(Finding.organization_id == tenant_id)
    if monitor_id is not None:
        stmt = stmt.where(Finding.monitor_id == monitor_id)
    if module:
        stmt = stmt.where(Finding.module_key == module)
    if severity:
        stmt = stmt.where(Finding.severity == severity)
    if status_filter:
        stmt = stmt.where(Finding.status == status_filter)
    stmt = stmt.order_by(Finding.detected_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


class FindingStatusUpdate(BaseModel):
    status: FindingStatus


@router.patch("/{finding_id}", response_model=FindingOut)
async def update_finding_status(
    finding_id: uuid.UUID,
    payload: FindingStatusUpdate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> Finding:
    result = await db.execute(
        select(Finding).where(Finding.id == finding_id, Finding.organization_id == tenant_id)
    )
    finding = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=404, detail="Bulgu bulunamadi")
    finding.status = payload.status
    await db.flush()
    await db.refresh(finding)
    return finding

"""Bulgu (Finding) uclari: listeleme, detay, durum guncelleme."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_tenant_id, get_current_user
from app.core_services.audit import record_audit
from app.models.finding import Finding, FindingStatus
from app.models.user import User
from app.schemas.monitor import FindingOut

router = APIRouter()


class StatsOut(BaseModel):
    total: int
    open: int  # new + triaged
    by_severity: dict[str, int]
    by_module: dict[str, int]
    by_day: list[dict]  # [{"day": "2026-06-01", "count": 3}, ...] son 14 gun


@router.get("/stats", response_model=StatsOut)
async def finding_stats(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> StatsOut:
    base = select(Finding).where(Finding.organization_id == tenant_id)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    open_count = (
        await db.execute(
            select(func.count()).select_from(
                base.where(
                    Finding.status.in_([FindingStatus.NEW, FindingStatus.TRIAGED])
                ).subquery()
            )
        )
    ).scalar_one()

    sev_rows = await db.execute(
        select(Finding.severity, func.count())
        .where(Finding.organization_id == tenant_id)
        .group_by(Finding.severity)
    )
    by_severity = {str(getattr(s, "value", s)): c for s, c in sev_rows.all()}

    mod_rows = await db.execute(
        select(Finding.module_key, func.count())
        .where(Finding.organization_id == tenant_id)
        .group_by(Finding.module_key)
    )
    by_module = {k: c for k, c in mod_rows.all()}

    since = datetime.now(timezone.utc) - timedelta(days=13)
    day_col = func.date_trunc("day", Finding.detected_at)
    day_rows = await db.execute(
        select(day_col.label("day"), func.count())
        .where(Finding.organization_id == tenant_id, Finding.detected_at >= since)
        .group_by(day_col)
        .order_by(day_col)
    )
    by_day = [{"day": d.date().isoformat(), "count": c} for d, c in day_rows.all()]

    return StatsOut(
        total=total,
        open=open_count,
        by_severity=by_severity,
        by_module=by_module,
        by_day=by_day,
    )


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
    user: User = Depends(get_current_user),
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
    record_audit(
        db,
        organization_id=tenant_id,
        user_id=user.id,
        action="finding.status",
        target_type="finding",
        target_id=str(finding.id),
        detail=payload.status.value,
    )
    await db.flush()
    await db.refresh(finding)
    return finding

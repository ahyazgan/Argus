"""Genel (modulden bagimsiz) monitor uclari: CRUD ve tarama tetikleme.

Yol: /m/{module_key}/...  -> herhangi bir canli modul icin calisir.
Erisim, tenant aboneliginde modulun acik olmasina baglidir.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_tenant_id, get_subscription
from app.models.monitor import Monitor
from app.models.subscription import Subscription
from app.models.task import Task, TaskStatus
from app.modules.catalog import CATALOG_BY_KEY
from app.schemas.monitor import MonitorCreate, MonitorOut, ScanTriggerOut

router = APIRouter()


async def module_access(
    module_key: str = Path(...),
    sub: Subscription = Depends(get_subscription),
):
    """Modulun canli ve bu tenant icin acik olmasini zorunlu kilar; meta'yi dondurur."""
    meta = CATALOG_BY_KEY.get(module_key)
    if meta is None or not meta.enabled:
        raise HTTPException(status_code=404, detail="Modul bulunamadi veya aktif degil")
    if module_key not in (sub.enabled_modules or []):
        raise HTTPException(
            status_code=403, detail=f"'{meta.name}' modulu aboneliginizde acik degil"
        )
    return meta


@router.post("/{module_key}/monitors", response_model=MonitorOut, status_code=201)
async def create_monitor(
    payload: MonitorCreate,
    module_key: str = Path(...),
    meta=Depends(module_access),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> Monitor:
    if payload.asset_type not in meta.asset_types:
        raise HTTPException(
            status_code=422,
            detail=f"Bu modul icin gecersiz varlik tipi. Secenekler: {meta.asset_types}",
        )
    monitor = Monitor(
        organization_id=tenant_id,
        module_key=module_key,
        name=payload.name,
        asset_type=payload.asset_type,
        asset_value=payload.asset_value,
    )
    db.add(monitor)
    await db.flush()
    await db.refresh(monitor)
    return monitor


@router.get("/{module_key}/monitors", response_model=list[MonitorOut])
async def list_monitors(
    module_key: str = Path(...),
    meta=Depends(module_access),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[Monitor]:
    result = await db.execute(
        select(Monitor)
        .where(Monitor.organization_id == tenant_id, Monitor.module_key == module_key)
        .order_by(Monitor.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_owned_monitor(
    monitor_id: uuid.UUID, module_key: str, tenant_id: uuid.UUID, db: AsyncSession
) -> Monitor:
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.organization_id == tenant_id,
            Monitor.module_key == module_key,
        )
    )
    monitor = result.scalar_one_or_none()
    if monitor is None:
        raise HTTPException(status_code=404, detail="Monitor bulunamadi")
    return monitor


@router.delete("/{module_key}/monitors/{monitor_id}", status_code=204)
async def delete_monitor(
    monitor_id: uuid.UUID,
    module_key: str = Path(...),
    meta=Depends(module_access),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    monitor = await _get_owned_monitor(monitor_id, module_key, tenant_id, db)
    await db.delete(monitor)


@router.post("/{module_key}/monitors/{monitor_id}/scan", response_model=ScanTriggerOut, status_code=202)
async def trigger_scan(
    monitor_id: uuid.UUID,
    module_key: str = Path(...),
    meta=Depends(module_access),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ScanTriggerOut:
    monitor = await _get_owned_monitor(monitor_id, module_key, tenant_id, db)

    task = Task(
        organization_id=tenant_id,
        monitor_id=monitor.id,
        module_key=module_key,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    celery_task_id = None
    try:
        from app.core_services.queue.scan_tasks import run_module_scan

        async_result = run_module_scan.delay(str(task.id), str(monitor.id))
        celery_task_id = async_result.id
        task.celery_task_id = celery_task_id
    except Exception:
        # Broker erisilemezse hata vermeden PENDING birak
        pass

    return ScanTriggerOut(task_id=task.id, celery_task_id=celery_task_id, status=task.status.value)


@router.get("/{module_key}/tasks/{task_id}", response_model=ScanTriggerOut)
async def get_task(
    task_id: uuid.UUID,
    module_key: str = Path(...),
    meta=Depends(module_access),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ScanTriggerOut:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.organization_id == tenant_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Gorev bulunamadi")
    return ScanTriggerOut(
        task_id=task.id, celery_task_id=task.celery_task_id, status=task.status.value
    )

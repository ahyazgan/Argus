"""Rapor uclari (cikti katmani): PDF disa aktarim."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_tenant_id
from app.models.finding import Finding
from app.models.tenant import Organization
from app.outputs.pdf import render_findings_pdf

router = APIRouter()


@router.get("/findings.pdf")
async def findings_pdf(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    monitor_id: uuid.UUID | None = Query(default=None),
    module: str | None = Query(default=None),
) -> Response:
    org = await db.get(Organization, tenant_id)

    stmt = select(Finding).where(Finding.organization_id == tenant_id)
    if monitor_id is not None:
        stmt = stmt.where(Finding.monitor_id == monitor_id)
    if module:
        stmt = stmt.where(Finding.module_key == module)
    stmt = stmt.order_by(Finding.detected_at.desc())
    result = await db.execute(stmt)
    findings = list(result.scalars().all())

    pdf_bytes = render_findings_pdf(org.name if org else "Argus", findings)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="argus-rapor.pdf"'},
    )

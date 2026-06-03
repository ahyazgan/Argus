"""Denetim kaydi yardimcisi - onemli mutasyonlari AuditLog'a yazar.

Async oturuma bir AuditLog ekler; isteyen endpoint'in oturumu commit'i halleder.
Denetim kaydi hicbir zaman ana islemi bozmamali (best-effort).
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def record_audit(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )

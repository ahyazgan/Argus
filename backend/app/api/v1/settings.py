"""Kurum ayarlari: bildirim webhook'lari ve dis entegrasyon API anahtari."""
from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_tenant_id
from app.models.tenant import Organization

router = APIRouter()


class SettingsOut(BaseModel):
    organization_name: str
    webhook_url: str | None
    slack_webhook_url: str | None
    has_api_key: bool


class SettingsUpdate(BaseModel):
    webhook_url: str | None = None
    slack_webhook_url: str | None = None


class ApiKeyOut(BaseModel):
    api_key: str


async def _get_org(tenant_id: uuid.UUID, db: AsyncSession) -> Organization:
    org = await db.get(Organization, tenant_id)
    assert org is not None
    return org


@router.get("", response_model=SettingsOut)
async def get_settings_view(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> SettingsOut:
    org = await _get_org(tenant_id, db)
    return SettingsOut(
        organization_name=org.name,
        webhook_url=org.webhook_url,
        slack_webhook_url=org.slack_webhook_url,
        has_api_key=bool(org.api_key),
    )


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsUpdate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> SettingsOut:
    org = await _get_org(tenant_id, db)
    if payload.webhook_url is not None:
        org.webhook_url = payload.webhook_url or None
    if payload.slack_webhook_url is not None:
        org.slack_webhook_url = payload.slack_webhook_url or None
    await db.flush()
    return SettingsOut(
        organization_name=org.name,
        webhook_url=org.webhook_url,
        slack_webhook_url=org.slack_webhook_url,
        has_api_key=bool(org.api_key),
    )


@router.post("/api-key", response_model=ApiKeyOut)
async def regenerate_api_key(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyOut:
    org = await _get_org(tenant_id, db)
    org.api_key = "argus_" + secrets.token_urlsafe(32)
    await db.flush()
    return ApiKeyOut(api_key=org.api_key)

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
    notify_email: str | None
    # GitHub / Jira cikti kanallari (token'lar govdede DONMEZ; yalnizca tanimli mi bilgisi)
    github_repo: str | None
    has_github_token: bool
    jira_base_url: str | None
    jira_email: str | None
    jira_project_key: str | None
    has_jira_token: bool
    gov_report_url: str | None
    has_gov_report_token: bool
    has_api_key: bool


class SettingsUpdate(BaseModel):
    webhook_url: str | None = None
    slack_webhook_url: str | None = None
    notify_email: str | None = None
    github_repo: str | None = None
    github_token: str | None = None
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_token: str | None = None
    jira_project_key: str | None = None
    gov_report_url: str | None = None
    gov_report_token: str | None = None


class ApiKeyOut(BaseModel):
    api_key: str


async def _get_org(tenant_id: uuid.UUID, db: AsyncSession) -> Organization:
    org = await db.get(Organization, tenant_id)
    assert org is not None
    return org


def _view(org: Organization) -> SettingsOut:
    return SettingsOut(
        organization_name=org.name,
        webhook_url=org.webhook_url,
        slack_webhook_url=org.slack_webhook_url,
        notify_email=org.notify_email,
        github_repo=org.github_repo,
        has_github_token=bool(org.github_token),
        jira_base_url=org.jira_base_url,
        jira_email=org.jira_email,
        jira_project_key=org.jira_project_key,
        has_jira_token=bool(org.jira_token),
        gov_report_url=org.gov_report_url,
        has_gov_report_token=bool(org.gov_report_token),
        has_api_key=bool(org.api_key),
    )


@router.get("", response_model=SettingsOut)
async def get_settings_view(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> SettingsOut:
    return _view(await _get_org(tenant_id, db))


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsUpdate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> SettingsOut:
    org = await _get_org(tenant_id, db)
    # Bos string => temizle (None). Token'lar yalnizca yeni deger gelince guncellenir
    # (bos birakilirsa mevcut token korunur).
    if payload.webhook_url is not None:
        org.webhook_url = payload.webhook_url or None
    if payload.slack_webhook_url is not None:
        org.slack_webhook_url = payload.slack_webhook_url or None
    if payload.notify_email is not None:
        org.notify_email = payload.notify_email or None
    if payload.github_repo is not None:
        org.github_repo = payload.github_repo or None
    if payload.github_token:
        org.github_token = payload.github_token
    if payload.jira_base_url is not None:
        org.jira_base_url = payload.jira_base_url or None
    if payload.jira_email is not None:
        org.jira_email = payload.jira_email or None
    if payload.jira_token:
        org.jira_token = payload.jira_token
    if payload.jira_project_key is not None:
        org.jira_project_key = payload.jira_project_key or None
    if payload.gov_report_url is not None:
        org.gov_report_url = payload.gov_report_url or None
    if payload.gov_report_token:
        org.gov_report_token = payload.gov_report_token
    await db.flush()
    return _view(org)


@router.post("/api-key", response_model=ApiKeyOut)
async def regenerate_api_key(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyOut:
    org = await _get_org(tenant_id, db)
    org.api_key = "argus_" + secrets.token_urlsafe(32)
    await db.flush()
    return ApiKeyOut(api_key=org.api_key)

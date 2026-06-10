"""Ekip / kullanici yonetimi uclari (org icinde cok kullanicili rol yonetimi).

Tenant kapsamlidir: tum islemler gecerli kullanicinin organizasyonuyla sinirlidir.
Kullanici olusturma/guncelleme/silme yalnizca OWNER ve ADMIN icindir.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_tenant_id, require_role
from app.core.security import hash_password
from app.core_services.audit import record_audit
from app.core_services.notifications.engine import send_email
from app.models.user import User, UserRole

router = APIRouter()


class TeamUserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)
    # API uzerinden yalnizca admin/member olusturulur (tek OWNER modeli korunur)
    role: UserRole = UserRole.MEMBER


class TeamUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class InviteCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=200)
    role: UserRole = UserRole.MEMBER


class InviteOut(BaseModel):
    email: str
    invite_link: str
    email_sent: bool


def _manager_roles():
    return require_role(UserRole.OWNER, UserRole.ADMIN)


@router.get("", response_model=list[TeamUserOut])
async def list_team(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    result = await db.execute(
        select(User).where(User.organization_id == tenant_id).order_by(User.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("", response_model=TeamUserOut, status_code=201)
async def create_team_user(
    payload: TeamUserCreate,
    manager: User = Depends(_manager_roles()),
    db: AsyncSession = Depends(get_db),
) -> User:
    if payload.role == UserRole.OWNER:
        raise HTTPException(status_code=422, detail="OWNER rolu API uzerinden atanamaz")
    email = payload.email.lower()
    exists = await db.execute(select(User).where(User.email == email))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayitli")
    user = User(
        organization_id=manager.organization_id,
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    record_audit(
        db,
        organization_id=manager.organization_id,
        user_id=manager.id,
        action="user.create",
        target_type="user",
        target_id=str(user.id),
        detail=f"{email} ({payload.role.value})",
    )
    return user


@router.post("/invite", response_model=InviteOut, status_code=201)
async def invite_team_user(
    payload: InviteCreate,
    manager: User = Depends(_manager_roles()),
    db: AsyncSession = Depends(get_db),
) -> InviteOut:
    """Bir kullaniciyi davet eder: pasif hesap + davet token'i olusturur, e-posta gonderir.

    SMTP yapilandirilmamissa davet linki yanitta doner (demo/elle paylasim icin).
    """
    if payload.role == UserRole.OWNER:
        raise HTTPException(status_code=422, detail="OWNER rolu davet edilemez")
    email = payload.email.lower()
    exists = await db.execute(select(User).where(User.email == email))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayitli")

    token = secrets.token_urlsafe(32)
    user = User(
        organization_id=manager.organization_id,
        email=email,
        # Kullanilamaz gecici parola; kabul sirasinda gercek parola belirlenir
        hashed_password=hash_password(secrets.token_urlsafe(16)),
        full_name=payload.full_name,
        role=payload.role,
        is_active=False,
        invite_token=token,
    )
    db.add(user)
    await db.flush()

    invite_link = f"{settings.frontend_origin}/accept-invite?token={token}"
    email_sent = send_email(
        email,
        "Argus Intelligence - ekip daveti",
        f"Ekibe davet edildiniz. Hesabinizi etkinlestirmek icin: {invite_link}",
    )
    record_audit(
        db,
        organization_id=manager.organization_id,
        user_id=manager.id,
        action="user.invite",
        target_type="user",
        target_id=str(user.id),
        detail=f"{email} ({payload.role.value})",
    )
    return InviteOut(email=email, invite_link=invite_link, email_sent=email_sent)


async def _get_member(user_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == tenant_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    return target


@router.patch("/{user_id}", response_model=TeamUserOut)
async def update_team_user(
    user_id: uuid.UUID,
    payload: TeamUserUpdate,
    manager: User = Depends(_manager_roles()),
    db: AsyncSession = Depends(get_db),
) -> User:
    target = await _get_member(user_id, manager.organization_id, db)
    if target.id == manager.id:
        raise HTTPException(status_code=409, detail="Kendi rolunuzu/durumunuzu degistiremezsiniz")
    if target.role == UserRole.OWNER:
        raise HTTPException(status_code=409, detail="OWNER hesabi degistirilemez")
    if payload.role is not None:
        if payload.role == UserRole.OWNER:
            raise HTTPException(status_code=422, detail="OWNER rolu atanamaz")
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active
    await db.flush()
    await db.refresh(target)
    record_audit(
        db,
        organization_id=manager.organization_id,
        user_id=manager.id,
        action="user.update",
        target_type="user",
        target_id=str(target.id),
        detail=f"rol={target.role.value} aktif={target.is_active}",
    )
    return target


@router.delete("/{user_id}", status_code=204)
async def delete_team_user(
    user_id: uuid.UUID,
    manager: User = Depends(_manager_roles()),
    db: AsyncSession = Depends(get_db),
) -> None:
    target = await _get_member(user_id, manager.organization_id, db)
    if target.id == manager.id:
        raise HTTPException(status_code=409, detail="Kendinizi silemezsiniz")
    if target.role == UserRole.OWNER:
        raise HTTPException(status_code=409, detail="OWNER hesabi silinemez")
    record_audit(
        db,
        organization_id=manager.organization_id,
        user_id=manager.id,
        action="user.delete",
        target_type="user",
        target_id=str(target.id),
        detail=target.email,
    )
    await db.delete(target)

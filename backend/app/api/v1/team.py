"""Ekip / kullanici yonetimi uclari (org icinde cok kullanicili rol yonetimi).

Tenant kapsamlidir: tum islemler gecerli kullanicinin organizasyonuyla sinirlidir.
Kullanici olusturma/guncelleme/silme yalnizca OWNER ve ADMIN icindir.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_tenant_id, require_role
from app.core.security import hash_password
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
    return user


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
    await db.delete(target)

"""Kimlik dogrulama uclari: kayit, giris, token yenileme, profil."""
from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.utils import slugify
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.tenant import Organization
from app.models.user import User, UserRole
from app.schemas.auth import (
    AcceptInviteRequest,
    RefreshRequest,
    RegisterRequest,
    Token,
    UserOut,
)

router = APIRouter()


async def _unique_slug(db: AsyncSession, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    i = 1
    while True:
        exists = await db.execute(select(Organization).where(Organization.slug == candidate))
        if exists.scalar_one_or_none() is None:
            return candidate
        i += 1
        candidate = f"{slug}-{i}"


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> Token:
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayitli")

    org = Organization(
        name=payload.organization_name,
        slug=await _unique_slug(db, payload.organization_name),
    )
    db.add(org)
    await db.flush()  # org.id

    # Yeni tenant Starter planla baslar, hicbir modul acik degil
    db.add(
        Subscription(
            organization_id=org.id,
            status=SubscriptionStatus.TRIALING,
            enabled_modules=[],
        )
    )

    user = User(
        organization_id=org.id,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER,
    )
    db.add(user)
    await db.flush()

    return Token(
        access_token=create_access_token(user.id, org.id),
        refresh_token=create_refresh_token(user.id, org.id),
    )


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    result = await db.execute(select(User).where(User.email == form.username.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="E-posta veya parola hatali")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Hesap pasif")
    return Token(
        access_token=create_access_token(user.id, user.organization_id),
        refresh_token=create_refresh_token(user.id, user.organization_id),
    )


@router.post("/refresh", response_model=Token)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> Token:
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Gecersiz token tipi")
        user_id = uuid.UUID(data["sub"])
        org_id = uuid.UUID(data["org"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Gecersiz yenileme token'i")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Kullanici bulunamadi")
    return Token(
        access_token=create_access_token(user.id, org_id),
        refresh_token=create_refresh_token(user.id, org_id),
    )


@router.post("/accept-invite", response_model=Token)
async def accept_invite(payload: AcceptInviteRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Davet token'i ile hesabi etkinlestirir: parola belirler ve oturum acar."""
    result = await db.execute(select(User).where(User.invite_token == payload.token))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="Gecersiz veya kullanilmis davet")
    user.hashed_password = hash_password(payload.password)
    user.is_active = True
    user.invite_token = None
    await db.flush()
    return Token(
        access_token=create_access_token(user.id, user.organization_id),
        refresh_token=create_refresh_token(user.id, user.organization_id),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user

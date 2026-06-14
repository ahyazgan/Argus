"""FastAPI bagimliliklari: gecerli kullanici, tenant kapsama ve modul erisim guard'i."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import API_KEY_PREFIX, decode_token, hash_api_key
from app.models.api_key import ApiKey
from app.models.subscription import Subscription
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# Programatik erisim icin API anahtari basligi (Swagger'da gorunur, zorunlu degil)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

_CRED_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Kimlik dogrulanamadi",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _authenticate_user(token: str, db: AsyncSession) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise _CRED_EXC
        user_id = payload.get("sub")
        if user_id is None:
            raise _CRED_EXC
    except jwt.PyJWTError:
        raise _CRED_EXC

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise _CRED_EXC
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _authenticate_user(token, db)


def _raw_api_key(request: Request, header_key: str | None) -> str | None:
    """API anahtarini X-API-Key veya 'Authorization: Bearer ak_...' icinden cikarir."""
    if header_key and header_key.startswith(API_KEY_PREFIX):
        return header_key
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        candidate = auth[7:]
        if candidate.startswith(API_KEY_PREFIX):
            return candidate
    return None


async def get_current_tenant_id(
    request: Request,
    header_key: str | None = Security(api_key_scheme),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Tenant kimligini API anahtari ya da JWT'den cozer (satir kapsama icin).

    Once API anahtari (X-API-Key veya Bearer ak_...) denenir; yoksa JWT'ye duser.
    """
    raw_key = _raw_api_key(request, header_key)
    if raw_key:
        rec = (
            await db.execute(select(ApiKey).where(ApiKey.hashed_key == hash_api_key(raw_key)))
        ).scalar_one_or_none()
        if rec is None or rec.revoked_at is not None:
            raise _CRED_EXC
        rec.last_used_at = datetime.now(timezone.utc)
        return rec.organization_id

    # JWT'ye dus
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token:
        raise _CRED_EXC
    user = await _authenticate_user(token, db)
    return user.organization_id


async def get_subscription(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> Subscription:
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == tenant_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Abonelik bulunamadi")
    return sub


def require_role(*allowed: UserRole):
    """Gecerli kullanicinin rolunu zorunlu kilan bagimlilik fabrikasi.

    Kullanim:  Depends(require_role(UserRole.OWNER, UserRole.ADMIN))
    """

    async def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu islem icin yetkiniz yok",
            )
        return user

    return _guard


def require_module(module_key: str):
    """Bir modulun bu tenant icin acik olmasini zorunlu kilan bagimlilik fabrikasi.

    Kullanim:  @router.get(..., dependencies=[Depends(require_module("darkweb"))])
    """

    async def _guard(sub: Subscription = Depends(get_subscription)) -> None:
        if module_key not in (sub.enabled_modules or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"'{module_key}' modulu aboneliginizde acik degil",
            )

    return _guard

"""FastAPI bagimliliklari: gecerli kullanici, tenant kapsama ve modul erisim guard'i."""
from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.subscription import Subscription
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_CRED_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Kimlik dogrulanamadi",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
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


def get_current_tenant_id(user: User = Depends(get_current_user)) -> uuid.UUID:
    """Gecerli kullanicinin tenant (organization) kimligi - satir kapsama icin."""
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

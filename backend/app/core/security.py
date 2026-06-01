"""Parola hashleme ve JWT token uretimi/dogrulama."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, org_id: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "org": org_id,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id),
        str(org_id),
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def create_refresh_token(user_id: uuid.UUID, org_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id),
        str(org_id),
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def decode_token(token: str) -> dict[str, Any]:
    """Token'i cozer; gecersizse jwt.PyJWTError firlatir."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

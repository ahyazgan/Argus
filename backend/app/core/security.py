"""Parola hashleme, JWT token ve API anahtari uretimi/dogrulama."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

API_KEY_PREFIX = "ak_"


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


# --- API anahtarlari ---------------------------------------------------------
# Anahtar formati: "ak_<32-bayt-base64url>". Yalnizca SHA-256 ozeti saklanir;
# ham anahtar yalnizca uretim aninda bir kez doner. Yuksek entropili oldugu
# icin bcrypt yerine sabit-zamanli karsilastirilan hizli hash kullanilir.


def generate_api_key() -> tuple[str, str, str]:
    """Yeni API anahtari uretir. Doner: (ham_anahtar, gosterim_oneki, ozet)."""
    raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return raw, api_key_display_prefix(raw), hash_api_key(raw)


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def api_key_display_prefix(raw: str) -> str:
    """Listede gosterilecek kisaltma (orn 'ak_Ab12…'). Gizli kismi acmaz."""
    return raw[: len(API_KEY_PREFIX) + 4] + "…"


def verify_api_key(raw: str, hashed: str) -> bool:
    return secrets.compare_digest(hash_api_key(raw), hashed)

"""Gercek-zamanli olay akisi (Server-Sent Events).

Tarayici EventSource'u ozel header gonderemedigi icin JWT, query parametresi (`token`)
olarak alinir ve dogrulanir. Akis, kullanicinin organizasyonuna ait olaylari yayar.
"""
from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.security import decode_token
from app.core_services.events import event_stream

router = APIRouter()


@router.get("/stream")
async def stream(token: str = Query(..., description="JWT access token")) -> StreamingResponse:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Gecersiz token tipi")
        org_id = uuid.UUID(payload["org"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Gecersiz token")

    return StreamingResponse(
        event_stream(org_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx tamponlamasini kapat
        },
    )

"""Gercek-zamanli olay yayini (Redis pub/sub) + SSE akisi.

Celery worker (sync) yeni bulgu uretince `publish_event` ile org kanalina yayinlar.
FastAPI SSE ucu (async) `event_stream` ile bu kanali dinleyip tarayiciya aktarir.
Redis erisilemezse yayin best-effort atlanir; akis bos/keepalive ile devam eder.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from app.core.config import settings

_CHANNEL_PREFIX = "argus:events:"


def channel_for(org_id) -> str:
    return f"{_CHANNEL_PREFIX}{org_id}"


def format_sse(event: dict) -> str:
    """Bir olayi SSE 'data:' cercevesine cevirir (saf)."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def publish_event(org_id, event: dict) -> bool:
    """Org kanalina olay yayinlar (sync; worker icinden). Hata durumunda False."""
    try:
        import redis

        client = redis.from_url(settings.redis_url)
        client.publish(channel_for(org_id), json.dumps(event))
        client.close()
        return True
    except Exception:
        return False


async def event_stream(org_id) -> AsyncIterator[str]:
    """Org kanalini dinleyip SSE cerceveleri uretir (heartbeat ile baglantiyi canli tutar)."""
    import redis.asyncio as aredis

    client = aredis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(channel_for(org_id))
    try:
        yield format_sse({"type": "connected"})
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if msg and msg.get("type") == "message":
                data = msg["data"]
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode()
                try:
                    event = json.loads(data)
                except (ValueError, TypeError):
                    event = {"type": "raw", "data": str(data)}
                yield format_sse(event)
            else:
                # Yorum satiri: proxy/baglanti zaman asimini onler
                yield ": keepalive\n\n"
    finally:
        try:
            await pubsub.unsubscribe(channel_for(org_id))
            await client.aclose()
        except Exception:
            pass

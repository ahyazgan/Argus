"""Zamanlanmis tarama icin saf (celery/DB'siz) yardimcilar.

Buradaki mantik kasitli olarak Celery ve veritabanindan bagimsizdir; boylece
birim testlerinde altyapi olmadan dogrulanabilir. Celery gorevi (scheduler.py)
monitorleri DB'den yukler ve bu fonksiyonlari kullanir.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Protocol

# API ve arayuzde sunulan izinli tarama araliklari (dakika).
# None => sadece manuel tarama.
ALLOWED_SCAN_INTERVALS: tuple[int, ...] = (15, 60, 360, 1440)  # 15dk, 1sa, 6sa, 24sa


class _MonitorLike(Protocol):
    is_active: bool
    scan_interval_minutes: int | None
    last_scanned_at: datetime | None


def is_due(
    interval_minutes: int | None,
    last_scanned_at: datetime | None,
    now: datetime,
) -> bool:
    """Bir monitorun simdi (now) otomatik taranmasi gerekip gerekmedigini soyler.

    - interval_minutes None/<=0 ise asla otomatik taranmaz (sadece manuel).
    - hic taranmamissa (last_scanned_at None) hemen vadesi gelmistir.
    - aksi halde son taramadan bu yana >= interval gectiyse vadesi gelmistir.
    """
    if not interval_minutes or interval_minutes <= 0:
        return False
    if last_scanned_at is None:
        return True
    return now - last_scanned_at >= timedelta(minutes=interval_minutes)


def select_due_monitors(monitors: Iterable[_MonitorLike], now: datetime) -> list[_MonitorLike]:
    """Aktif ve vadesi gelmis monitorleri dondurur (dispatcher bunlari kuyruga atar)."""
    return [
        m
        for m in monitors
        if m.is_active and is_due(m.scan_interval_minutes, m.last_scanned_at, now)
    ]

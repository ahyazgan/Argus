"""Monitor ve bulgu (Finding) semalari."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core_services.queue.scheduling import ALLOWED_SCAN_INTERVALS


def _validate_interval(value: int | None) -> int | None:
    """None (manuel) ya da izinli araliklardan biri olmali."""
    if value is None:
        return None
    if value not in ALLOWED_SCAN_INTERVALS:
        raise ValueError(
            f"Gecersiz tarama araligi. Izinli degerler (dakika): {list(ALLOWED_SCAN_INTERVALS)} "
            "veya bos (manuel)."
        )
    return value


class MonitorCreate(BaseModel):
    module_key: str = Field(default="darkweb")
    name: str = Field(min_length=1, max_length=200)
    asset_type: str  # domain | email | keyword
    asset_value: str = Field(min_length=1, max_length=500)
    # None => sadece manuel; aksi halde her N dakikada otomatik tarama
    scan_interval_minutes: int | None = None

    _check_interval = field_validator("scan_interval_minutes")(_validate_interval)


class MonitorScheduleUpdate(BaseModel):
    """Bir monitorun zamanlanmis tarama araligini ayarlar/kaldirir."""

    scan_interval_minutes: int | None = None

    _check_interval = field_validator("scan_interval_minutes")(_validate_interval)


class MonitorOut(BaseModel):
    id: uuid.UUID
    module_key: str
    name: str
    asset_type: str
    asset_value: str
    is_active: bool
    scan_interval_minutes: int | None
    last_scanned_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingOut(BaseModel):
    id: uuid.UUID
    monitor_id: uuid.UUID
    module_key: str
    title: str
    severity: str
    status: str
    summary: str | None
    recommendation: str | None
    source: str
    asset_value: str
    raw_data: dict
    detected_at: datetime

    model_config = {"from_attributes": True}


class ScanTriggerOut(BaseModel):
    task_id: uuid.UUID
    celery_task_id: str | None
    status: str

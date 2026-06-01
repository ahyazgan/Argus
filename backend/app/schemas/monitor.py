"""Monitor ve bulgu (Finding) semalari."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MonitorCreate(BaseModel):
    module_key: str = Field(default="darkweb")
    name: str = Field(min_length=1, max_length=200)
    asset_type: str  # domain | email | keyword
    asset_value: str = Field(min_length=1, max_length=500)


class MonitorOut(BaseModel):
    id: uuid.UUID
    module_key: str
    name: str
    asset_type: str
    asset_value: str
    is_active: bool
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

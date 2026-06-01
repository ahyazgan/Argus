"""Modul katalogu ve abonelik semalari."""
from __future__ import annotations

from pydantic import BaseModel


class ModuleOut(BaseModel):
    key: str
    name: str
    description: str
    category: str
    asset_types: list[str]
    available: bool  # platformda canli mi ("yakinda" degil)
    enabled: bool  # bu tenant icin acik mi


class ToggleModuleRequest(BaseModel):
    module_key: str
    enable: bool


class SubscriptionOut(BaseModel):
    plan: str
    plan_name: str
    status: str
    module_limit: int
    enabled_modules: list[str]
    price_label: str

"""Abonelik plan kademeleri ve modul limitleri (gorseldeki fiyatlandirma)."""
from __future__ import annotations

import enum
from dataclasses import dataclass


class PlanTier(str, enum.Enum):
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class PlanSpec:
    tier: PlanTier
    name: str
    module_limit: int  # ayni anda acik olabilecek maksimum modul
    price_label: str


PLANS: dict[PlanTier, PlanSpec] = {
    PlanTier.STARTER: PlanSpec(PlanTier.STARTER, "Starter", 2, "$299/ay"),
    PlanTier.PRO: PlanSpec(PlanTier.PRO, "Pro", 5, "$999/ay"),
    # Enterprise: tum moduller (9) -> pratikte sinirsiz
    PlanTier.ENTERPRISE: PlanSpec(PlanTier.ENTERPRISE, "Enterprise", 99, "$4K-$20K/ay"),
}


def module_limit_for(tier: PlanTier) -> int:
    return PLANS[tier].module_limit

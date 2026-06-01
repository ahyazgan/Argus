"""Modul katalogu ve tenant bazli ac/kapa uclari."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db
from app.core.deps import get_subscription
from app.core.plans import PLANS, PlanTier, module_limit_for
from app.models.subscription import Subscription
from app.modules.catalog import CATALOG, CATALOG_BY_KEY
from app.schemas.module import ModuleOut, SubscriptionOut, ToggleModuleRequest

router = APIRouter()


@router.get("", response_model=list[ModuleOut])
async def list_modules(sub: Subscription = Depends(get_subscription)) -> list[ModuleOut]:
    enabled = set(sub.enabled_modules or [])
    return [
        ModuleOut(
            key=m.key,
            name=m.name,
            description=m.description,
            category=m.category,
            asset_types=m.asset_types,
            available=m.enabled,
            enabled=m.key in enabled,
        )
        for m in CATALOG
    ]


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription_info(sub: Subscription = Depends(get_subscription)) -> SubscriptionOut:
    spec = PLANS[sub.plan]
    return SubscriptionOut(
        plan=sub.plan.value,
        plan_name=spec.name,
        status=sub.status.value,
        module_limit=spec.module_limit,
        enabled_modules=sub.enabled_modules or [],
        price_label=spec.price_label,
    )


@router.post("/toggle", response_model=SubscriptionOut)
async def toggle_module(
    payload: ToggleModuleRequest,
    sub: Subscription = Depends(get_subscription),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    meta = CATALOG_BY_KEY.get(payload.module_key)
    if meta is None:
        raise HTTPException(status_code=404, detail="Bilinmeyen modul")

    enabled = list(sub.enabled_modules or [])

    if payload.enable:
        if not meta.enabled:
            raise HTTPException(status_code=409, detail=f"'{meta.name}' henuz yayinda degil (yakinda)")
        if payload.module_key in enabled:
            pass  # zaten acik
        else:
            limit = module_limit_for(sub.plan)
            if len(enabled) >= limit:
                raise HTTPException(
                    status_code=403,
                    detail=f"Plan limiti asildi ({limit} modul). Plani yukseltin.",
                )
            enabled.append(payload.module_key)
    else:
        enabled = [k for k in enabled if k != payload.module_key]

    sub.enabled_modules = enabled
    flag_modified(sub, "enabled_modules")
    await db.flush()

    spec = PLANS[sub.plan]
    return SubscriptionOut(
        plan=sub.plan.value,
        plan_name=spec.name,
        status=sub.status.value,
        module_limit=spec.module_limit,
        enabled_modules=enabled,
        price_label=spec.price_label,
    )

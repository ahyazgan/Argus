"""Odeme uclari (cikti/cekirdek): plan listesi, Stripe checkout (stub), plan degistirme."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_subscription
from app.core.plans import PLANS, PlanTier
from app.models.subscription import Subscription

router = APIRouter()


class PlanOut(BaseModel):
    tier: str
    name: str
    module_limit: int
    price_label: str


class CheckoutRequest(BaseModel):
    plan: PlanTier


class CheckoutResponse(BaseModel):
    stripe_enabled: bool
    checkout_url: str | None
    message: str


class ChangePlanRequest(BaseModel):
    plan: PlanTier


@router.get("/plans", response_model=list[PlanOut])
async def list_plans() -> list[PlanOut]:
    return [
        PlanOut(tier=s.tier.value, name=s.name, module_limit=s.module_limit, price_label=s.price_label)
        for s in PLANS.values()
    ]


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(payload: CheckoutRequest) -> CheckoutResponse:
    """Stripe checkout oturumu. STRIPE_ENABLED=false ise stub doner (gercek cagri yok)."""
    if not settings.stripe_enabled or not settings.stripe_secret_key:
        return CheckoutResponse(
            stripe_enabled=False,
            checkout_url=None,
            message=(
                f"Stripe devre disi (stub). '{payload.plan.value}' plani icin gercek odeme "
                "akisi STRIPE_ENABLED=true ve STRIPE_SECRET_KEY ayarlandiginda etkinlesir."
            ),
        )
    # Gercek entegrasyon (etkinlestiginde):
    #   import stripe; stripe.api_key = settings.stripe_secret_key
    #   session = stripe.checkout.Session.create(...)
    #   return CheckoutResponse(stripe_enabled=True, checkout_url=session.url, message="ok")
    raise HTTPException(status_code=501, detail="Stripe entegrasyonu henuz tamamlanmadi")


@router.post("/change-plan", response_model=PlanOut)
async def change_plan(
    payload: ChangePlanRequest,
    sub: Subscription = Depends(get_subscription),
    db: AsyncSession = Depends(get_db),
) -> PlanOut:
    """Plan kademesini degistirir (stub - gercek odeme olmadan; test/limit gosterimi icin).

    Yeni limit, halihazirda acik modul sayisindan kucukse reddedilir.
    """
    new_spec = PLANS[payload.plan]
    open_count = len(sub.enabled_modules or [])
    if open_count > new_spec.module_limit:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{new_spec.name} plani {new_spec.module_limit} modul destekler ama "
                f"{open_count} modulunuz acik. Once bazi modulleri kapatin."
            ),
        )
    sub.plan = payload.plan
    await db.flush()
    return PlanOut(
        tier=new_spec.tier.value,
        name=new_spec.name,
        module_limit=new_spec.module_limit,
        price_label=new_spec.price_label,
    )

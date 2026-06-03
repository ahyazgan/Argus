"""Odeme uclari (cikti/cekirdek): plan listesi, Stripe checkout + webhook, plan degistirme."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_tenant_id, get_subscription
from app.core.plans import PLANS, PlanTier
from app.models.subscription import Subscription, SubscriptionStatus

router = APIRouter()

# Plan kademesi -> Stripe Price ID eslemesi (config'ten)
_PRICE_BY_PLAN: dict[PlanTier, str] = {
    PlanTier.STARTER: settings.stripe_price_starter,
    PlanTier.PRO: settings.stripe_price_pro,
    PlanTier.ENTERPRISE: settings.stripe_price_enterprise,
}


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
async def create_checkout(
    payload: CheckoutRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
) -> CheckoutResponse:
    """Stripe checkout oturumu olusturur. STRIPE_ENABLED=false ise stub doner."""
    if not settings.stripe_enabled or not settings.stripe_secret_key:
        return CheckoutResponse(
            stripe_enabled=False,
            checkout_url=None,
            message=(
                f"Stripe devre disi (stub). '{payload.plan.value}' plani icin gercek odeme "
                "akisi STRIPE_ENABLED=true ve STRIPE_SECRET_KEY ayarlandiginda etkinlesir."
            ),
        )

    price_id = _PRICE_BY_PLAN.get(payload.plan)
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"'{payload.plan.value}' plani icin STRIPE_PRICE_* ayarlanmamis.",
        )

    import stripe

    stripe.api_key = settings.stripe_secret_key
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.frontend_origin}/billing?checkout=success",
            cancel_url=f"{settings.frontend_origin}/billing?checkout=cancel",
            metadata={"organization_id": str(tenant_id), "plan": payload.plan.value},
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Stripe hatasi: {exc}") from exc

    return CheckoutResponse(stripe_enabled=True, checkout_url=session.url, message="ok")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Stripe webhook'u: imzayi dogrular ve abonelik durumunu gunceller (kimlik dogrulamasiz).

    - checkout.session.completed -> plani metadata'dan uygula, durumu ACTIVE yap, stripe id'leri kaydet
    - customer.subscription.deleted -> durumu CANCELED yap
    """
    if not settings.stripe_enabled:
        raise HTTPException(status_code=404, detail="Stripe devre disi")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    import stripe

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as exc:  # noqa: BLE001 - imza/parse hatasi
        raise HTTPException(status_code=400, detail=f"Gecersiz webhook: {exc}") from exc

    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        meta = obj.get("metadata") or {}
        org_id = meta.get("organization_id")
        plan_value = meta.get("plan")
        if org_id and plan_value:
            sub = (
                await db.execute(
                    select(Subscription).where(
                        Subscription.organization_id == uuid.UUID(org_id)
                    )
                )
            ).scalar_one_or_none()
            if sub is not None:
                try:
                    sub.plan = PlanTier(plan_value)
                except ValueError:
                    pass
                sub.status = SubscriptionStatus.ACTIVE
                sub.stripe_customer_id = obj.get("customer")
                sub.stripe_subscription_id = obj.get("subscription")
                await db.flush()

    elif etype == "customer.subscription.deleted":
        sub_id = obj.get("id")
        if sub_id:
            sub = (
                await db.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id == sub_id
                    )
                )
            ).scalar_one_or_none()
            if sub is not None:
                sub.status = SubscriptionStatus.CANCELED
                await db.flush()

    return {"received": True}


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

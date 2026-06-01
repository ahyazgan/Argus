"""Subscription modeli - plan kademesi ve acik moduller."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, uuid_pk
from app.core.plans import PlanTier

if TYPE_CHECKING:
    from app.models.tenant import Organization


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True
    )
    plan: Mapped[PlanTier] = mapped_column(
        SAEnum(PlanTier, name="plan_tier", values_callable=lambda e: [m.value for m in e]),
        default=PlanTier.STARTER,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(
            SubscriptionStatus,
            name="subscription_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=SubscriptionStatus.TRIALING,
        nullable=False,
    )
    # Acik modul anahtarlari (orn ["darkweb"])
    enabled_modules: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    # Stripe (stub - simdilik kullanilmiyor)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="subscription")

"""Monitor modeli - bir modulun izledigi varlik (domain, e-posta, anahtar kelime...)."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.finding import Finding


class Monitor(Base, TimestampMixin):
    __tablename__ = "monitors"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    module_key: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)  # domain | email | keyword
    asset_value: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    findings: Mapped[list["Finding"]] = relationship(
        back_populates="monitor", cascade="all, delete-orphan"
    )

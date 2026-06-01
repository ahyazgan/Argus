"""Finding modeli - bir taramada uretilen, Claude ile triyaj edilmis bulgu/uyari."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.monitor import Monitor


class FindingSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(str, enum.Enum):
    NEW = "new"
    TRIAGED = "triaged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), index=True
    )
    module_key: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        SAEnum(
            FindingSeverity,
            name="finding_severity",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=FindingSeverity.INFO,
        nullable=False,
    )
    status: Mapped[FindingStatus] = mapped_column(
        SAEnum(
            FindingStatus,
            name="finding_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=FindingStatus.NEW,
        nullable=False,
    )
    # Claude'un urettigi Turkce ozet + onerilen aksiyon
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_value: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    monitor: Mapped["Monitor"] = relationship(back_populates="findings")

"""Organization (tenant) modeli - multi-tenancy kok varligi."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.subscription import Subscription
    from app.models.user import User


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)

    # Bildirim kanallari (Slack/webhook) - yeni bulguda tetiklenir
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # E-posta bildirimi (adres bossa atlanir; SMTP ayarlari da gereklidir)
    notify_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # GitHub Issues cikti kanali
    github_repo: Mapped[str | None] = mapped_column(String(140), nullable=True)  # "owner/repo"
    github_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Jira cikti kanali
    jira_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jira_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    jira_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jira_project_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Kamu/BTK ihbar entegrasyonu (yapilandirilabilir uc nokta)
    gov_report_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gov_report_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Dis entegrasyon (REST API) icin API anahtari
    api_key: Mapped[str | None] = mapped_column(String(80), unique=True, index=True, nullable=True)

    users: Mapped[list["User"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )

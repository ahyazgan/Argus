"""initial baseline - tum cekirdek tablolar

Argus Intelligence semasinin ilk Alembic baseline'i. Modeller (app/models) ile
elle eslenmistir. Taze veritabaninda uygulama acilista `create_all` da kullanir;
uretimde ise migration zinciri tercih edilir:

    alembic upgrade head

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def _ts_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("slack_webhook_url", sa.String(500), nullable=True),
        sa.Column("notify_email", sa.String(320), nullable=True),
        sa.Column("github_repo", sa.String(140), nullable=True),
        sa.Column("github_token", sa.String(255), nullable=True),
        sa.Column("jira_base_url", sa.String(255), nullable=True),
        sa.Column("jira_email", sa.String(320), nullable=True),
        sa.Column("jira_token", sa.String(255), nullable=True),
        sa.Column("jira_project_key", sa.String(40), nullable=True),
        sa.Column("gov_report_url", sa.String(500), nullable=True),
        sa.Column("gov_report_token", sa.String(255), nullable=True),
        sa.Column("report_schedule", sa.String(10), server_default="none", nullable=False),
        sa.Column("last_report_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("api_key", sa.String(80), nullable=True),
        *_ts_columns(),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_index("ix_organizations_api_key", "organizations", ["api_key"], unique=True)

    # users
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=True),
        sa.Column(
            "role",
            sa.Enum("owner", "admin", "member", name="user_role"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("invite_token", sa.String(80), nullable=True),
        *_ts_columns(),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_invite_token", "users", ["invite_token"], unique=True)

    # subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "organization_id",
            UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("plan", sa.Enum("starter", "pro", "enterprise", name="plan_tier"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "trialing", "past_due", "canceled", name="subscription_status"),
            nullable=False,
        ),
        sa.Column("enabled_modules", JSONB, nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        *_ts_columns(),
    )

    # monitors
    op.create_table(
        "monitors",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_key", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("asset_value", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("scan_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        *_ts_columns(),
    )
    op.create_index("ix_monitors_organization_id", "monitors", ["organization_id"])
    op.create_index("ix_monitors_module_key", "monitors", ["module_key"])

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("monitor_id", UUID, sa.ForeignKey("monitors.id", ondelete="CASCADE"), nullable=True),
        sa.Column("module_key", sa.String(50), nullable=False),
        sa.Column("celery_task_id", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "failed", name="task_status"),
            nullable=False,
        ),
        sa.Column("findings_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_ts_columns(),
    )
    op.create_index("ix_tasks_organization_id", "tasks", ["organization_id"])
    op.create_index("ix_tasks_celery_task_id", "tasks", ["celery_task_id"])

    # findings
    op.create_table(
        "findings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("monitor_id", UUID, sa.ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_key", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("info", "low", "medium", "high", "critical", name="finding_severity"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("new", "triaged", "resolved", "false_positive", name="finding_status"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("asset_value", sa.String(500), nullable=False),
        sa.Column("raw_data", JSONB, nullable=False),
        sa.Column("assigned_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=True),
        sa.Column("seen_count", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *_ts_columns(),
        sa.UniqueConstraint("monitor_id", "fingerprint", name="uq_finding_monitor_fingerprint"),
    )
    op.create_index("ix_findings_organization_id", "findings", ["organization_id"])
    op.create_index("ix_findings_monitor_id", "findings", ["monitor_id"])
    op.create_index("ix_findings_module_key", "findings", ["module_key"])
    op.create_index("ix_findings_fingerprint", "findings", ["fingerprint"])

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", sa.String(80), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # finding_comments
    op.create_table(
        "finding_comments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("finding_id", UUID, sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finding_comments_finding_id", "finding_comments", ["finding_id"])


def downgrade() -> None:
    op.drop_table("finding_comments")
    op.drop_table("audit_logs")
    op.drop_table("findings")
    op.drop_table("tasks")
    op.drop_table("monitors")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.drop_table("organizations")
    for enum_name in (
        "finding_status",
        "finding_severity",
        "task_status",
        "subscription_status",
        "plan_tier",
        "user_role",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

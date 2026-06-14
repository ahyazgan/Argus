"""organizations.webhook_secret - genel webhook HMAC imza sirri

Revision ID: 0003_webhook_secret
Revises: 0002_api_keys
Create Date: 2026-06-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_webhook_secret"
down_revision = "0002_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("webhook_secret", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "webhook_secret")

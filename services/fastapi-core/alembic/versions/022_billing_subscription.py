"""billing_subscription — Stripe customer/plan on tenant, subscriptions,
webhook event idempotency table

Revision ID: 022_billing_subscription
Revises: 021_slack_publication_channel
Create Date: 2026-08-10
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "022_billing_subscription"
down_revision: Union[str, None] = "021_slack_publication_channel"
branch_labels = None
depends_on = None

_SUBSCRIPTION_STATUSES = (
    "ACTIVE",
    "TRIALING",
    "PAST_DUE",
    "CANCELED",
    "INCOMPLETE",
    "INCOMPLETE_EXPIRED",
    "UNPAID",
)


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("stripe_customer_id", sa.String(255), nullable=True, unique=True),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "billing_plan",
            sa.String(20),
            nullable=False,
            server_default="free",
        ),
    )

    # sa.Enum auto-creates the Postgres type as a side effect of create_table
    # (via a before_create event) — no separate .create() call needed/wanted.
    subscription_status = sa.Enum(*_SUBSCRIPTION_STATUSES, name="subscription_status")

    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stripe_subscription_id", sa.String(255), nullable=False, unique=True
        ),
        sa.Column("stripe_price_id", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column(
            "current_period_start", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
    )

    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("stripe_event_id", sa.String(255), nullable=False, unique=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_stripe_webhook_events_stripe_event_id",
        "stripe_webhook_events",
        ["stripe_event_id"],
    )


def downgrade() -> None:
    op.drop_table("stripe_webhook_events")
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_tenant_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    # op.drop_table already drops the enum type as a side effect (mirrors the
    # auto-create on create_table) — checkfirst guards against the same
    # double-operation bug that hit CREATE TYPE on upgrade().
    sa.Enum(name="subscription_status").drop(op.get_bind(), checkfirst=True)
    op.drop_column("tenants", "billing_plan")
    op.drop_column("tenants", "stripe_customer_id")

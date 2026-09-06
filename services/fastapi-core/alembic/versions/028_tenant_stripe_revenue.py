"""tenant_stripe_credentials + tenant_stripe_webhook_events — a tenant's OWN
Stripe account (their downstream customers), used for revenue analytics.

Revision ID: 028_tenant_stripe_revenue
Revises: 027_content_recommendations
Create Date: 2026-08-25
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

revision: str = "028_tenant_stripe_revenue"
down_revision: Union[str, None] = "027_content_recommendations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_stripe_credentials",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "owner_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("secret_key_encrypted", sa.Text, nullable=False),
        sa.Column("secret_key_last4", sa.String(4), nullable=False),
        sa.Column("webhook_secret_encrypted", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_table(
        "tenant_stripe_webhook_events",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # A charge/event ID is unique within one Stripe account but a
        # different tenant's Stripe account could (extremely rarely) produce
        # a colliding ID — scope idempotency to (tenant_id, stripe_event_id),
        # not stripe_event_id alone, unlike OpenGrow's own single-account
        # StripeWebhookEvent table.
        sa.Column("stripe_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_tenant_stripe_webhook_events_tenant_event",
        "tenant_stripe_webhook_events",
        ["tenant_id", "stripe_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tenant_stripe_webhook_events_tenant_event",
        table_name="tenant_stripe_webhook_events",
    )
    op.drop_table("tenant_stripe_webhook_events")
    op.drop_table("tenant_stripe_credentials")

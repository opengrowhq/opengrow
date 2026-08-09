"""analytics_connectors — store GA4 and GSC connector config

Revision ID: 008_analytics_connectors
Revises: 007_analytics_channels_dedupe
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008_analytics_connectors"
down_revision: Union[str, None] = "007_analytics_channels_dedupe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    provider = postgresql.ENUM(
        "ga4",
        "gsc",
        name="analytics_connector_provider",
        create_type=False,
    )
    status = postgresql.ENUM(
        "NEEDS_AUTH",
        "CONNECTED",
        "DISCONNECTED",
        name="analytics_connector_status",
        create_type=False,
    )
    provider.create(op.get_bind(), checkfirst=True)
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "analytics_connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider", provider, nullable=False),
        sa.Column("status", status, nullable=False, server_default="NEEDS_AUTH"),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("external_property_id", sa.String(200), nullable=True),
        sa.Column("site_url", sa.String(600), nullable=True),
        sa.Column("scopes", postgresql.JSONB, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_analytics_connectors_tenant_id", "analytics_connectors", ["tenant_id"]
    )
    op.create_index(
        "ix_analytics_connectors_owner_id", "analytics_connectors", ["owner_id"]
    )
    op.create_index(
        "ix_analytics_connectors_provider", "analytics_connectors", ["provider"]
    )
    op.create_index(
        "ix_analytics_connectors_status", "analytics_connectors", ["status"]
    )
    op.create_index(
        "ix_analytics_connectors_is_deleted", "analytics_connectors", ["is_deleted"]
    )


def downgrade() -> None:
    op.drop_table("analytics_connectors")
    postgresql.ENUM(name="analytics_connector_status").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="analytics_connector_provider").drop(
        op.get_bind(), checkfirst=True
    )

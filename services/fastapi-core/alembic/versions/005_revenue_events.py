"""revenue_events — attribution events for published content

Revision ID: 005_revenue_events
Revises: 004_brands
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005_revenue_events"
down_revision: Union[str, None] = "004_brands"
branch_labels = None
depends_on = None


def upgrade() -> None:
    event_type = postgresql.ENUM(
        "VISIT",
        "SIGNUP",
        "LEAD",
        "CUSTOMER",
        "REVENUE",
        name="revenue_event_type",
        create_type=False,
    )
    event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "revenue_events",
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
        sa.Column(
            "content_piece_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_pieces.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("source_url", sa.String(600), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_revenue_events_tenant_id", "revenue_events", ["tenant_id"])
    op.create_index("ix_revenue_events_owner_id", "revenue_events", ["owner_id"])
    op.create_index(
        "ix_revenue_events_content_piece_id",
        "revenue_events",
        ["content_piece_id"],
    )
    op.create_index("ix_revenue_events_event_type", "revenue_events", ["event_type"])
    op.create_index("ix_revenue_events_is_deleted", "revenue_events", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("revenue_events")
    postgresql.ENUM(name="revenue_event_type").drop(op.get_bind(), checkfirst=True)

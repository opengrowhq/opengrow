"""analytics_channels_dedupe — normalize imported attribution rows

Revision ID: 007_analytics_channels_dedupe
Revises: 006_revenue_event_count
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_analytics_channels_dedupe"
down_revision: Union[str, None] = "006_revenue_event_count"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("revenue_events", sa.Column("provider", sa.String(24), nullable=True))
    op.add_column("revenue_events", sa.Column("channel", sa.String(48), nullable=True))
    op.add_column(
        "revenue_events", sa.Column("dedupe_key", sa.String(64), nullable=True)
    )
    op.create_index("ix_revenue_events_provider", "revenue_events", ["provider"])
    op.create_index("ix_revenue_events_channel", "revenue_events", ["channel"])
    op.create_index("ix_revenue_events_dedupe_key", "revenue_events", ["dedupe_key"])
    op.create_index(
        "uq_revenue_events_tenant_dedupe_key",
        "revenue_events",
        ["tenant_id", "dedupe_key"],
        unique=True,
        postgresql_where=sa.text("dedupe_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_revenue_events_tenant_dedupe_key", table_name="revenue_events")
    op.drop_index("ix_revenue_events_dedupe_key", table_name="revenue_events")
    op.drop_index("ix_revenue_events_channel", table_name="revenue_events")
    op.drop_index("ix_revenue_events_provider", table_name="revenue_events")
    op.drop_column("revenue_events", "dedupe_key")
    op.drop_column("revenue_events", "channel")
    op.drop_column("revenue_events", "provider")

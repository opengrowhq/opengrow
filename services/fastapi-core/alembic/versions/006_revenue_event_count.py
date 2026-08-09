"""revenue_event_count — aggregate imported analytics rows

Revision ID: 006_revenue_event_count
Revises: 005_revenue_events
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_revenue_event_count"
down_revision: Union[str, None] = "005_revenue_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "revenue_events",
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("revenue_events", "event_count")

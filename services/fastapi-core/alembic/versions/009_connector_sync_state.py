"""connector_sync_state — track analytics connector sync attempts

Revision ID: 009_connector_sync_state
Revises: 008_analytics_connectors
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_connector_sync_state"
down_revision: Union[str, None] = "008_analytics_connectors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE analytics_connector_status ADD VALUE IF NOT EXISTS 'SYNCING'"
    )
    op.execute("ALTER TYPE analytics_connector_status ADD VALUE IF NOT EXISTS 'ERROR'")
    op.add_column(
        "analytics_connectors",
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "analytics_connectors",
        sa.Column("last_sync_error", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analytics_connectors", "last_sync_error")
    op.drop_column("analytics_connectors", "last_sync_at")

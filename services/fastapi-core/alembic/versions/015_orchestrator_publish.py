"""orchestrator_publish — optional auto-publish target on a run

Revision ID: 015_orchestrator_publish
Revises: 014_orchestrator_runs
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "015_orchestrator_publish"
down_revision: Union[str, None] = "014_orchestrator_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orchestrator_runs", sa.Column("publish_channel", sa.String(32), nullable=True)
    )
    op.add_column(
        "orchestrator_runs", sa.Column("publish_config", JSONB, nullable=True)
    )


def downgrade() -> None:
    op.drop_column("orchestrator_runs", "publish_config")
    op.drop_column("orchestrator_runs", "publish_channel")

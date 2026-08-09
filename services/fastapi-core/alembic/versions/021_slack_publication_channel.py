"""slack_publication_channel — add SLACK channel

Revision ID: 021_slack_publication_channel
Revises: 020_audit_log
Create Date: 2026-08-09
"""

from typing import Union

from alembic import op

revision: str = "021_slack_publication_channel"
down_revision: Union[str, None] = "020_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE publication_channel ADD VALUE IF NOT EXISTS 'SLACK'")


def downgrade() -> None:
    # Postgres cannot drop enum values; no-op (values are additive/harmless).
    pass

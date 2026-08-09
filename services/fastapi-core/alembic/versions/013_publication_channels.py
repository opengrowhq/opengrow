"""publication_channels — add WordPress/Ghost/Webflow/X/LinkedIn/Email channels

Revision ID: 013_publication_channels
Revises: 012_usage_ledger
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op

revision: str = "013_publication_channels"
down_revision: Union[str, None] = "012_usage_ledger"
branch_labels = None
depends_on = None

_VALUES = ["WORDPRESS", "GHOST", "WEBFLOW", "X", "LINKEDIN", "EMAIL"]


def upgrade() -> None:
    for value in _VALUES:
        op.execute(f"ALTER TYPE publication_channel ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres cannot drop enum values; no-op (values are additive/harmless).
    pass

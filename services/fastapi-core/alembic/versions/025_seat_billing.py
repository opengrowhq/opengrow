"""seat_billing — seat-overage line item tracking on subscriptions

Revision ID: 025_seat_billing
Revises: 024_invites
Create Date: 2026-08-11
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "025_seat_billing"
down_revision: Union[str, None] = "024_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("stripe_seat_item_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("extra_seats", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "extra_seats")
    op.drop_column("subscriptions", "stripe_seat_item_id")

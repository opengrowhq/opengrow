"""credit_balance — prepaid, non-expiring usage credits on tenant

Revision ID: 023_credit_balance
Revises: 022_billing_subscription
Create Date: 2026-08-10
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "023_credit_balance"
down_revision: Union[str, None] = "022_billing_subscription"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "credit_balance_cents",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "credit_balance_cents")

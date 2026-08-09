"""usage_ledger — per-tenant metering records

Revision ID: 012_usage_ledger
Revises: 011_api_keys
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "012_usage_ledger"
down_revision: Union[str, None] = "011_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("units", sa.Integer, nullable=False, server_default="1"),
        sa.Column("cost_units", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ref_type", sa.String(50), nullable=True),
        sa.Column("ref_id", sa.String(64), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_ledger_tenant_id", "usage_ledger", ["tenant_id"])
    op.create_index("ix_usage_ledger_kind", "usage_ledger", ["kind"])
    op.create_index("ix_usage_ledger_is_deleted", "usage_ledger", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("usage_ledger")

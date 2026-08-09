"""brands — Brand DNA profiles extracted from a website

Revision ID: 004_brands
Revises: 003_publications
Create Date: 2026-07-21
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_brands"
down_revision: Union[str, None] = "003_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    brand_status = postgresql.ENUM(
        "PENDING",
        "SCRAPING",
        "EXTRACTING",
        "READY",
        "FAILED",
        name="brand_status",
        create_type=False,
    )
    brand_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "brands",
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
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(600), nullable=True),
        sa.Column("status", brand_status, nullable=False, server_default="PENDING"),
        sa.Column("profile", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_brands_tenant_id", "brands", ["tenant_id"])
    op.create_index("ix_brands_owner_id", "brands", ["owner_id"])
    op.create_index("ix_brands_status", "brands", ["status"])
    op.create_index("ix_brands_is_deleted", "brands", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("brands")
    postgresql.ENUM(name="brand_status").drop(op.get_bind(), checkfirst=True)

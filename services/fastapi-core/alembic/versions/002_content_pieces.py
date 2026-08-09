"""content_pieces — editorial lifecycle over generated content

Revision ID: 002_content_pieces
Revises: 001_initial
Create Date: 2026-07-21
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_content_pieces"
down_revision: Union[str, None] = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    content_status = postgresql.ENUM(
        "DRAFT",
        "IN_REVIEW",
        "APPROVED",
        "PUBLISHED",
        "ARCHIVED",
        name="content_status",
        create_type=False,
    )
    content_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "content_pieces",
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
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("format", sa.String(60), nullable=True),
        sa.Column("status", content_status, nullable=False, server_default="DRAFT"),
        sa.Column(
            "source_generation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_pieces_tenant_id", "content_pieces", ["tenant_id"])
    op.create_index("ix_content_pieces_owner_id", "content_pieces", ["owner_id"])
    op.create_index("ix_content_pieces_status", "content_pieces", ["status"])
    op.create_index("ix_content_pieces_is_deleted", "content_pieces", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("content_pieces")
    postgresql.ENUM(name="content_status").drop(op.get_bind(), checkfirst=True)

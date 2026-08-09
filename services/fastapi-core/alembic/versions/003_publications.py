"""publications — publish a content piece to an external channel (GitHub PR)

Revision ID: 003_publications
Revises: 002_content_pieces
Create Date: 2026-07-21
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_publications"
down_revision: Union[str, None] = "002_content_pieces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    channel = postgresql.ENUM(
        "GITHUB_PR", name="publication_channel", create_type=False
    )
    channel.create(op.get_bind(), checkfirst=True)

    pub_status = postgresql.ENUM(
        "PENDING",
        "PUBLISHING",
        "PR_OPENED",
        "PUBLISHED",
        "FAILED",
        name="publication_status",
        create_type=False,
    )
    pub_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "publications",
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
        sa.Column(
            "content_piece_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_pieces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", channel, nullable=False),
        sa.Column("status", pub_status, nullable=False, server_default="PENDING"),
        sa.Column("target", postgresql.JSONB, nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("external_ref", sa.String(200), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_publications_tenant_id", "publications", ["tenant_id"])
    op.create_index("ix_publications_owner_id", "publications", ["owner_id"])
    op.create_index(
        "ix_publications_content_piece_id", "publications", ["content_piece_id"]
    )
    op.create_index("ix_publications_status", "publications", ["status"])
    op.create_index("ix_publications_is_deleted", "publications", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("publications")
    postgresql.ENUM(name="publication_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="publication_channel").drop(op.get_bind(), checkfirst=True)

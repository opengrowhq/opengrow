"""github_credentials — per-tenant GitHub PAT storage

Revision ID: 016_github_credentials
Revises: 015_orchestrator_publish
Create Date: 2026-07-25
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "016_github_credentials"
down_revision: Union[str, None] = "015_orchestrator_publish"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_credentials",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("token_encrypted", sa.Text(), nullable=False),
        sa.Column("token_last4", sa.String(length=4), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_github_credentials_owner_id"),
        "github_credentials",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_github_credentials_tenant_id"),
        "github_credentials",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_github_credentials_is_deleted"),
        "github_credentials",
        ["is_deleted"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_github_credentials_is_deleted"), table_name="github_credentials"
    )
    op.drop_index(
        op.f("ix_github_credentials_tenant_id"), table_name="github_credentials"
    )
    op.drop_index(
        op.f("ix_github_credentials_owner_id"), table_name="github_credentials"
    )
    op.drop_table("github_credentials")

"""orchestrator_runs — persisted content-cycle run state machine

Revision ID: 014_orchestrator_runs
Revises: 013_publication_channels
Create Date: 2026-07-22
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID

revision: str = "014_orchestrator_runs"
down_revision: Union[str, None] = "013_publication_channels"
branch_labels = None
depends_on = None

_STATUS = ("QUEUED", "GENERATING", "PROMOTING", "COMPLETE", "FAILED")


def upgrade() -> None:
    # create_type=False so create_table below doesn't try to CREATE TYPE again.
    status = ENUM(*_STATUS, name="orchestrator_run_status", create_type=False)
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "orchestrator_runs",
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
        sa.Column("brief", sa.Text, nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column(
            "status",
            status,
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column("step", sa.String(50), nullable=True),
        sa.Column(
            "generation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("generations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "content_piece_id",
            UUID(as_uuid=True),
            sa.ForeignKey("content_pieces.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_orchestrator_runs_tenant_id", "orchestrator_runs", ["tenant_id"]
    )
    op.create_index("ix_orchestrator_runs_status", "orchestrator_runs", ["status"])
    op.create_index(
        "ix_orchestrator_runs_is_deleted", "orchestrator_runs", ["is_deleted"]
    )


def downgrade() -> None:
    op.drop_table("orchestrator_runs")
    ENUM(name="orchestrator_run_status").drop(op.get_bind(), checkfirst=True)

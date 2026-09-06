"""invites — pending team-member invitations for a tenant

Revision ID: 024_invites
Revises: 021_slack_publication_channel
Create Date: 2026-08-10
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "024_invites"
down_revision: Union[str, None] = "021_slack_publication_channel"
branch_labels = None
depends_on = None

_INVITE_STATUSES = ("PENDING", "ACCEPTED", "REVOKED")


def upgrade() -> None:
    # sa.Enum auto-creates the Postgres type as a side effect of create_table
    # (via a before_create event) — no separate .create() call needed/wanted.
    invite_status = sa.Enum(*_INVITE_STATUSES, name="invite_status")

    op.create_table(
        "invites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("status", invite_status, nullable=False, server_default="PENDING"),
        sa.Column(
            "invited_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_invites_tenant_id", "invites", ["tenant_id"])
    op.create_index("ix_invites_email", "invites", ["email"])
    op.create_index("ix_invites_token", "invites", ["token"], unique=True)
    op.create_index("ix_invites_status", "invites", ["status"])


def downgrade() -> None:
    op.drop_index("ix_invites_status", table_name="invites")
    op.drop_index("ix_invites_token", table_name="invites")
    op.drop_index("ix_invites_email", table_name="invites")
    op.drop_index("ix_invites_tenant_id", table_name="invites")
    op.drop_table("invites")
    # op.drop_table already drops the enum type as a side effect (mirrors the
    # auto-create on create_table) — checkfirst guards against a double-drop
    # of the enum.
    sa.Enum(name="invite_status").drop(op.get_bind(), checkfirst=True)

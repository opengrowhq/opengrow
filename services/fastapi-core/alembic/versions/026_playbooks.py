"""playbooks — versioned prompt/methodology templates

Revision ID: 026_playbooks
Revises: 024_invites
Create Date: 2026-08-24
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

revision: str = "026_playbooks"
down_revision: Union[str, None] = "024_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    playbook_kind = sa.Enum(
        "ARTICLE_OUTLINE",
        "ARTICLE_DRAFT",
        "GENERIC_COPY",
        name="playbook_kind",
    )
    op.create_table(
        "playbooks",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("kind", playbook_kind, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("system_template", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    # Partial unique index: at most one active version per (tenant_id, kind),
    # including the global default row where tenant_id IS NULL.
    op.execute(
        """
        CREATE UNIQUE INDEX ix_playbooks_one_active_per_tenant_kind
        ON playbooks (kind, COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'))
        WHERE is_active = true AND is_deleted = false
        """
    )
    op.create_index("ix_playbooks_tenant_kind", "playbooks", ["tenant_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_playbooks_tenant_kind", table_name="playbooks")
    op.execute("DROP INDEX IF EXISTS ix_playbooks_one_active_per_tenant_kind")
    op.drop_table("playbooks")
    sa.Enum(name="playbook_kind").drop(op.get_bind(), checkfirst=True)

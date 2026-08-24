"""content_recommendations — attribution-loop refresh/new-topic suggestions

Revision ID: 027_content_recommendations
Revises: 026_playbooks
Create Date: 2026-08-24
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

revision: str = "027_content_recommendations"
down_revision: Union[str, None] = "026_playbooks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    kind = sa.Enum(
        "REFRESH", "DOUBLE_DOWN", "NEW_TOPIC", name="content_recommendation_kind"
    )
    rec_status = sa.Enum(
        "PENDING", "ACTIONED", "DISMISSED", name="content_recommendation_status"
    )
    op.create_table(
        "content_recommendations",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kind", kind, nullable=False),
        sa.Column(
            "content_piece_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("content_pieces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column(
            "status",
            rec_status,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "orchestrator_run_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("orchestrator_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
    op.create_index(
        "ix_content_recommendations_tenant_status",
        "content_recommendations",
        ["tenant_id", "status"],
    )
    # A content piece shouldn't accumulate duplicate open (PENDING) refresh
    # recommendations across repeated sweeps — dismissed/actioned rows are
    # excluded so old resolved history never blocks a fresh suggestion.
    op.execute(
        """
        CREATE UNIQUE INDEX ix_content_recommendations_one_pending_per_piece_kind
        ON content_recommendations (content_piece_id, kind)
        WHERE status = 'PENDING' AND content_piece_id IS NOT NULL AND is_deleted = false
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_content_recommendations_one_pending_per_piece_kind"
    )
    op.drop_index(
        "ix_content_recommendations_tenant_status",
        table_name="content_recommendations",
    )
    op.drop_table("content_recommendations")
    sa.Enum(name="content_recommendation_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="content_recommendation_kind").drop(op.get_bind(), checkfirst=True)

"""generation_lineage — parent_generation_id self-FK on generations

Tracks which generation a follow-up was derived from (e.g. an article_draft
pointing at its article_outline), first-class instead of a metadata_json key.

Revision ID: 018_generation_lineage
Revises: 017_asset_embeddings
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018_generation_lineage"
down_revision = "017_asset_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generations",
        sa.Column("parent_generation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_generations_parent_generation_id",
        "generations",
        "generations",
        ["parent_generation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_generations_parent_generation_id",
        "generations",
        ["parent_generation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_generations_parent_generation_id", table_name="generations")
    op.drop_constraint(
        "fk_generations_parent_generation_id", "generations", type_="foreignkey"
    )
    op.drop_column("generations", "parent_generation_id")

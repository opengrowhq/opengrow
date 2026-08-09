"""asset_embeddings — store embedding vector + text snippet for retrieval

Revision ID: 017_asset_embeddings
Revises: 016_github_credentials
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "017_asset_embeddings"
down_revision = "016_github_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("embedding", postgresql.JSONB(), nullable=True))
    op.add_column("assets", sa.Column("text_snippet", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "text_snippet")
    op.drop_column("assets", "embedding")

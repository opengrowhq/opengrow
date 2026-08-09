"""orchestrator_outline_approval — AWAITING_OUTLINE_APPROVAL run status

Adds the human-pause state used by the article pipeline (design C): the
worker stops after the outline step and waits for an explicit approval
before drafting. PG 12+ allows ADD VALUE inside Alembic's transaction as
long as the new value is not used in the same transaction (it is not);
enum values cannot be removed, so there is no downgrade.

Revision ID: 019_outline_approval
Revises: 018_generation_lineage
"""

from alembic import op

revision = "019_outline_approval"
down_revision = "018_generation_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE orchestrator_run_status "
        "ADD VALUE IF NOT EXISTS 'AWAITING_OUTLINE_APPROVAL'"
    )


def downgrade() -> None:
    # PostgreSQL enum values cannot be dropped; leaving the value is harmless.
    pass

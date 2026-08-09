import enum
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class OrchestratorRunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    PROMOTING = "PROMOTING"
    AWAITING_OUTLINE_APPROVAL = "AWAITING_OUTLINE_APPROVAL"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class OrchestratorRun(TenantMixin, Base):
    """A persisted content-cycle run: brief → generate → promote to content.

    The state machine (Phase 2 skeleton) is intentionally short so it proves the
    mechanism before scoring/keyword/publish steps are added. `generation_id` and
    `content_piece_id` link to the artifacts each step produced.
    """

    __tablename__ = "orchestrator_runs"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[OrchestratorRunStatus] = mapped_column(
        SAEnum(OrchestratorRunStatus, name="orchestrator_run_status"),
        default=OrchestratorRunStatus.QUEUED,
        nullable=False,
        index=True,
    )
    step: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("generations.id", ondelete="SET NULL"),
        nullable=True,
    )
    content_piece_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("content_pieces.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Optional auto-publish after promote (opt-in). Config holds BYOK creds.
    publish_channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    publish_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

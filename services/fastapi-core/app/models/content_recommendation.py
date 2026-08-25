import enum
from uuid import UUID

from sqlalchemy import Float, ForeignKey, String, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class ContentRecommendationKind(str, enum.Enum):
    REFRESH = "REFRESH"  # a published piece is decaying — revise/update it
    DOUBLE_DOWN = "DOUBLE_DOWN"  # a piece is growing — write more like it
    NEW_TOPIC = "NEW_TOPIC"  # a gap in topic/tag coverage vs. what's published


class ContentRecommendationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIONED = "ACTIONED"
    DISMISSED = "DISMISSED"


class ContentRecommendation(TenantMixin, Base):
    """A suggestion computed from real attribution data (RevenueEvent trends)
    for what to write or refresh next — closes the orchestrator's "Phase 6"
    attribution loop: data collection -> trend analysis -> suggestion ->
    optionally starts a new orchestrator run.

    Never edited in place: a fresh sweep creates new PENDING rows (a partial
    unique index blocks a second PENDING row for the same content_piece_id +
    kind), and existing rows are marked ACTIONED/DISMISSED rather than
    deleted, so history of what was suggested and what happened to it
    survives.
    """

    __tablename__ = "content_recommendations"

    kind: Mapped[ContentRecommendationKind] = mapped_column(
        SAEnum(ContentRecommendationKind, name="content_recommendation_kind"),
        nullable=False,
    )
    content_piece_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("content_pieces.id", ondelete="CASCADE"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[ContentRecommendationStatus] = mapped_column(
        SAEnum(ContentRecommendationStatus, name="content_recommendation_status"),
        default=ContentRecommendationStatus.PENDING,
        nullable=False,
    )
    orchestrator_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orchestrator_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

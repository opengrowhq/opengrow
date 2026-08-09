import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class RevenueEventType(str, enum.Enum):
    VISIT = "VISIT"
    SIGNUP = "SIGNUP"
    LEAD = "LEAD"
    CUSTOMER = "CUSTOMER"
    REVENUE = "REVENUE"


class RevenueEvent(TenantMixin, Base):
    """Tenant-scoped event used to attribute business outcomes to content."""

    __tablename__ = "revenue_events"

    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    content_piece_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("content_pieces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[RevenueEventType] = mapped_column(
        SAEnum(RevenueEventType, name="revenue_event_type"),
        nullable=False,
        index=True,
    )
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    provider: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    channel: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    dedupe_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    source_url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class UsageLedger(TenantMixin, Base):
    """Append-only per-tenant usage record — the metering mechanism.

    `units` counts billable actions (e.g. 1 per generation); `cost_units` is the
    metered cost (tokens/credits) when known. Enforcement (quotas) is layered on
    top separately; this table only records.
    """

    __tablename__ = "usage_ledger"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ref_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

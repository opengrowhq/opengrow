import enum
from uuid import UUID

from sqlalchemy import String, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class BrandStatus(str, enum.Enum):
    PENDING = "PENDING"
    SCRAPING = "SCRAPING"
    EXTRACTING = "EXTRACTING"
    READY = "READY"
    FAILED = "FAILED"


class Brand(TenantMixin, Base):
    """A brand profile ("Brand DNA") extracted from a website + editable by the user.

    `profile` holds the structured result: tone, palette, tagline, audience,
    pains, do/don't phrases. Generations condition on this instead of an ad-hoc
    reference asset.
    """

    __tablename__ = "brands"

    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    status: Mapped[BrandStatus] = mapped_column(
        SAEnum(BrandStatus, name="brand_status"),
        default=BrandStatus.PENDING,
        nullable=False,
        index=True,
    )
    profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

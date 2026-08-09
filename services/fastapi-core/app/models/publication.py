import enum
from uuid import UUID

from sqlalchemy import String, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class PublicationChannel(str, enum.Enum):
    GITHUB_PR = "GITHUB_PR"
    WORDPRESS = "WORDPRESS"
    GHOST = "GHOST"
    WEBFLOW = "WEBFLOW"
    X = "X"
    LINKEDIN = "LINKEDIN"
    EMAIL = "EMAIL"
    SLACK = "SLACK"


class PublicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    PUBLISHING = "PUBLISHING"
    PR_OPENED = "PR_OPENED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class Publication(TenantMixin, Base):
    """A record of publishing a ContentPiece to an external channel.

    The first channel is GitHub PR publishing (the wedge). `target` holds the
    channel-specific destination (repo/path/branch); `url`/`external_ref` hold
    the result (PR URL / number).
    """

    __tablename__ = "publications"

    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    content_piece_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("content_pieces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[PublicationChannel] = mapped_column(
        SAEnum(PublicationChannel, name="publication_channel"),
        nullable=False,
    )
    status: Mapped[PublicationStatus] = mapped_column(
        SAEnum(PublicationStatus, name="publication_status"),
        default=PublicationStatus.PENDING,
        nullable=False,
        index=True,
    )
    target: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

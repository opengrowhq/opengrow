import enum
from uuid import UUID

from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class ContentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ContentPiece(TenantMixin, Base):
    """A publishable unit of content with an editorial lifecycle.

    Raw `Generation` rows are model outputs; a ContentPiece is the product object
    that carries a title, editable body, status, and provenance, and is what the
    publishing layer (Markdown export, GitHub PR, …) acts on.
    """

    __tablename__ = "content_pieces"

    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Free-form format tag, e.g. blog_post, tweet, ad, email_sequence.
    format: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        SAEnum(ContentStatus, name="content_status"),
        default=ContentStatus.DRAFT,
        nullable=False,
        index=True,
    )
    # Provenance: the generation this content was derived from (if any).
    source_generation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("generations.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

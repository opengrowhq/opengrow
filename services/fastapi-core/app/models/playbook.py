import enum
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, SoftDeleteMixin, TimestampMixin


class PlaybookKind(str, enum.Enum):
    ARTICLE_OUTLINE = "ARTICLE_OUTLINE"
    ARTICLE_DRAFT = "ARTICLE_DRAFT"
    GENERIC_COPY = "GENERIC_COPY"


class Playbook(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A versioned system-prompt template ("methodology playbook").

    ``tenant_id`` NULL means a global default (seeded from the previously
    hardcoded prompt constants); a tenant row overrides the global default
    for that ``kind``. At most one row per (tenant_id, kind) has
    ``is_active=True`` — enforced by a partial unique index, not app code,
    so races can't create two active versions. New versions are inserted as
    new rows rather than edited in place, so history is preserved.
    """

    __tablename__ = "playbooks"

    tenant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    kind: Mapped[PlaybookKind] = mapped_column(
        SAEnum(PlaybookKind, name="playbook_kind"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    system_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

import enum
from uuid import UUID

from sqlalchemy import String, Integer, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class AssetStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"  # in temp bucket, pending scan
    SCANNING = "SCANNING"
    SCAN_FAILED = "SCAN_FAILED"  # ClamAV FOUND or ERROR
    SCANNED = "SCANNED"  # moved to assets bucket
    EMBEDDING = "EMBEDDING"
    INDEXED = "INDEXED"  # Qdrant point live
    EMBED_FAILED = "EMBED_FAILED"


class Asset(TenantMixin, Base):
    __tablename__ = "assets"

    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    temp_object_key: Mapped[str] = mapped_column(String(400), nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(400), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(
        SAEnum(AssetStatus, name="asset_status"),
        default=AssetStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    scan_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Retrieval support: the embedding vector and a bounded text extract. Lite mode
    # ranks these in Postgres; production also mirrors the vector into Qdrant.
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    text_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

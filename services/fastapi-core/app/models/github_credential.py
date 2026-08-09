from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class GitHubCredential(TenantMixin, Base):
    """Tenant-scoped GitHub publishing credential.

    Stores a tenant-provided PAT for hosted/multi-tenant publishing. Responses
    must only expose metadata such as token_last4, never token_encrypted.
    """

    __tablename__ = "github_credentials"

    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    token_last4: Mapped[str] = mapped_column(String(4), nullable=False)

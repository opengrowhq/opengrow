import enum
import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID

from app.database import Base
from app.models.base import TenantMixin


class InviteStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"


def generate_invite_token() -> str:
    # URL-safe, high-entropy — this is the sole credential an accept request
    # needs, so it must not be guessable (not a sequential id, not derived
    # from anything predictable like email+timestamp).
    return secrets.token_urlsafe(32)


class Invite(TenantMixin, Base):
    """A pending (or resolved) invitation for someone to join a tenant."""

    __tablename__ = "invites"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    status: Mapped[InviteStatus] = mapped_column(
        SAEnum(InviteStatus, name="invite_status"),
        nullable=False,
        default=InviteStatus.PENDING,
        index=True,
    )
    invited_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

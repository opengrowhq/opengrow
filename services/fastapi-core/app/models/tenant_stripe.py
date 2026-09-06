from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TenantMixin, TimestampMixin


class TenantStripeCredential(TenantMixin, Base):
    """A tenant's OWN Stripe account credential (their downstream customers'
    payments). OpenGrow's core has no platform billing (removed in 0.3.0);
    this is per-tenant BYOK revenue attribution. Mirrors GitHubCredential's
    BYOK shape exactly.
    """

    __tablename__ = "tenant_stripe_credentials"

    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    secret_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    secret_key_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    webhook_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)


class TenantStripeWebhookEvent(IdMixin, TimestampMixin, Base):
    """Idempotency log for a tenant's own Stripe webhook deliveries. Scoped
    to (tenant_id, stripe_event_id) rather than a global-unique event ID:
    this table sees events from many independent tenant-owned Stripe
    accounts, so uniqueness must be scoped per tenant.
    """

    __tablename__ = "tenant_stripe_webhook_events"

    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stripe_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

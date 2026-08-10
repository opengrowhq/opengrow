import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class SubscriptionStatus(str, enum.Enum):
    """Mirrors Stripe's Subscription.status values."""

    ACTIVE = "ACTIVE"
    TRIALING = "TRIALING"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    INCOMPLETE = "INCOMPLETE"
    INCOMPLETE_EXPIRED = "INCOMPLETE_EXPIRED"
    UNPAID = "UNPAID"


class Subscription(TenantMixin, Base):
    """One row per tenant's Stripe subscription (at most one active at a time)."""

    __tablename__ = "subscriptions"

    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False)  # "pro" | "team"
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        index=True,
    )
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # The seat-overage line item's Stripe subscription-item id (distinct
    # from `stripe_subscription_id`, which is the base plan's item on this
    # same subscription) — None until a Team tenant actually has more
    # members than settings.TEAM_INCLUDED_SEATS. Needed to update the
    # existing item's quantity rather than creating a duplicate each time.
    stripe_seat_item_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

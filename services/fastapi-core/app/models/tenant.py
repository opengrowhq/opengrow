from sqlalchemy import String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class Tenant(IdMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    billing_plan: Mapped[str] = mapped_column(
        String(20), nullable=False, default="free"
    )
    # Prepaid, non-expiring usage credits (cents). Only ever increases (plan
    # grants on billing-period renewal, purchased top-ups) or decreases
    # (metered usage). Never resets to zero, never expires — deliberate:
    # "hard-stop errors on exhausted credits instead of silent overage
    # billing" is a documented product decision, not a missing feature.
    credit_balance_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

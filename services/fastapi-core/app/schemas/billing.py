from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CheckoutRequest(BaseModel):
    plan: str  # "pro" | "team"

    @field_validator("plan")
    @classmethod
    def lower(cls, v: str) -> str:
        return v.strip().lower()


class CheckoutOut(BaseModel):
    checkout_url: str


class TopupRequest(BaseModel):
    amount_eur_cents: int  # must be one of app.core.credits.TOPUP_TIERS_EUR_CENTS


class PortalOut(BaseModel):
    portal_url: str


class SubscriptionOut(BaseModel):
    billing_plan: str
    subscription_status: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False

"""Stripe billing — Checkout, Billing Portal, and webhook sync.

Hosted-only: uses Stripe-hosted Checkout and Billing Portal pages, not a
custom payment/cancel UI (PCI scope + retry/proration/dunning logic are
Stripe's problem, not ours). See `docs/billing-slice2-plan` context in
opengrow-internal for the full rationale.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.authz import authz_client
from app.core.credits import PLAN_MONTHLY_GRANT_CENTS, grant_credits
from app.database import get_db
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.stripe_webhook_event import StripeWebhookEvent
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.billing import (
    CheckoutOut,
    CheckoutRequest,
    PortalOut,
    SubscriptionOut,
)

router = APIRouter()

_PRICE_IDS = {
    "pro": settings.STRIPE_PRICE_ID_PRO,
    "team": settings.STRIPE_PRICE_ID_TEAM,
}

# Stripe's subscription.status values map 1:1 onto our enum by upper-casing.
_STRIPE_STATUS_MAP = {s.value.lower(): s for s in SubscriptionStatus}


def _client() -> stripe.StripeClient:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Billing is not configured"
        )
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


async def _assert_tenant_admin(current: User) -> None:
    if not await authz_client.check(
        str(current.id), "admin", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only a tenant admin can manage billing"
        )


async def _get_or_create_stripe_customer(
    db: AsyncSession, client: stripe.StripeClient, tenant: Tenant, current: User
) -> str:
    if tenant.stripe_customer_id:
        return tenant.stripe_customer_id
    customer = client.v1.customers.create(
        params={
            "email": current.email,
            "metadata": {"opengrow_tenant_id": str(tenant.id)},
        }
    )
    tenant.stripe_customer_id = customer.id
    await db.commit()
    return customer.id


@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    payload: CheckoutRequest,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_admin(current)
    price_id = _PRICE_IDS.get(payload.plan)
    if not price_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown plan: {payload.plan}")

    client = _client()
    tenant = await db.get(Tenant, current.tenant_id)
    customer_id = await _get_or_create_stripe_customer(db, client, tenant, current)

    session = client.v1.checkout.sessions.create(
        params={
            "mode": "subscription",
            "customer": customer_id,
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{settings.FRONTEND_BASE_URL}/settings/billing?checkout=success",
            "cancel_url": f"{settings.FRONTEND_BASE_URL}/settings/billing?checkout=cancelled",
            "metadata": {"opengrow_tenant_id": str(tenant.id), "opengrow_plan": payload.plan},
        }
    )
    return CheckoutOut(checkout_url=session.url)


@router.post("/portal", response_model=PortalOut)
async def create_portal_session(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_admin(current)
    tenant = await db.get(Tenant, current.tenant_id)
    if not tenant.stripe_customer_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No billing account yet — subscribe first"
        )

    client = _client()
    session = client.v1.billing_portal.sessions.create(
        params={
            "customer": tenant.stripe_customer_id,
            "return_url": f"{settings.FRONTEND_BASE_URL}/settings/billing",
        }
    )
    return PortalOut(portal_url=session.url)


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tenant = await db.get(Tenant, current.tenant_id)
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.tenant_id == current.tenant_id,
            Subscription.is_deleted.is_(False),
        )
    )
    return SubscriptionOut(
        billing_plan=tenant.billing_plan,
        subscription_status=sub.status.value if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook is not configured"
        )
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            body, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid webhook: {e}") from e

    existing = await db.scalar(
        select(StripeWebhookEvent).where(
            StripeWebhookEvent.stripe_event_id == event["id"]
        )
    )
    if existing:
        return {"status": "already_processed"}

    obj = event["data"]["object"]
    event_type = event["type"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, obj)
    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        await _handle_subscription_updated(db, obj)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, obj)

    db.add(
        StripeWebhookEvent(
            id=uuid4(),
            stripe_event_id=event["id"],
            event_type=event_type,
            payload=event.to_dict_recursive(),
            processed_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    return {"status": "processed"}


async def _tenant_by_stripe_customer(db: AsyncSession, customer_id: str) -> Tenant | None:
    return await db.scalar(select(Tenant).where(Tenant.stripe_customer_id == customer_id))


async def _handle_checkout_completed(db: AsyncSession, session: dict) -> None:
    tenant_id = (session.get("metadata") or {}).get("opengrow_tenant_id")
    if not tenant_id:
        return
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    plan = (session.get("metadata") or {}).get("opengrow_plan", "pro")
    tenant.billing_plan = plan
    await db.commit()


async def _upsert_subscription(db: AsyncSession, sub: dict) -> None:
    tenant = await _tenant_by_stripe_customer(db, sub["customer"])
    if tenant is None:
        return
    status_value = _STRIPE_STATUS_MAP.get(sub["status"], SubscriptionStatus.INCOMPLETE)
    item = sub["items"]["data"][0]
    price_id = item["price"]["id"]
    plan = "team" if price_id == settings.STRIPE_PRICE_ID_TEAM else "pro"

    existing = await db.scalar(
        select(Subscription).where(
            Subscription.stripe_subscription_id == sub["id"]
        )
    )
    period_start = datetime.fromtimestamp(item["current_period_start"], tz=timezone.utc)
    period_end = datetime.fromtimestamp(item["current_period_end"], tz=timezone.utc)
    # A new billing period has begun if this is the first time we're seeing
    # the subscription, or the period start advanced past what we had on
    # file — either way, the plan's monthly credit grant is due.
    is_new_period = existing is None or existing.current_period_start != period_start

    if existing:
        existing.stripe_price_id = price_id
        existing.plan = plan
        existing.status = status_value
        existing.current_period_start = period_start
        existing.current_period_end = period_end
        existing.cancel_at_period_end = bool(sub.get("cancel_at_period_end"))
    else:
        db.add(
            Subscription(
                id=uuid4(),
                tenant_id=tenant.id,
                stripe_subscription_id=sub["id"],
                stripe_price_id=price_id,
                plan=plan,
                status=status_value,
                current_period_start=period_start,
                current_period_end=period_end,
                cancel_at_period_end=bool(sub.get("cancel_at_period_end")),
            )
        )
    tenant.billing_plan = plan if status_value == SubscriptionStatus.ACTIVE else tenant.billing_plan
    await db.commit()

    if is_new_period and status_value == SubscriptionStatus.ACTIVE:
        grant_cents = PLAN_MONTHLY_GRANT_CENTS.get(plan)
        if grant_cents:
            await grant_credits(db, tenant_id=tenant.id, amount_cents=grant_cents)


async def _handle_subscription_updated(db: AsyncSession, sub: dict) -> None:
    await _upsert_subscription(db, sub)


async def _handle_subscription_deleted(db: AsyncSession, sub: dict) -> None:
    tenant = await _tenant_by_stripe_customer(db, sub["customer"])
    if tenant is None:
        return
    existing = await db.scalar(
        select(Subscription).where(Subscription.stripe_subscription_id == sub["id"])
    )
    if existing:
        existing.status = SubscriptionStatus.CANCELED
    tenant.billing_plan = "free"
    await db.commit()

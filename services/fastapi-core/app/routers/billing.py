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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.authz import authz_client
from app.core.credits import (
    PLAN_MONTHLY_GRANT_CENTS,
    TOPUP_TIERS_EUR_CENTS,
    grant_credits,
    topup_credit_cents,
)
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
    TopupRequest,
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
    if payload.plan not in _PRICE_IDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown plan: {payload.plan}")

    client = _client()
    price_id = _PRICE_IDS[payload.plan]
    if not price_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Billing is not configured"
        )
    tenant = await db.get(Tenant, current.tenant_id)
    customer_id = await _get_or_create_stripe_customer(db, client, tenant, current)

    line_items = [{"price": price_id, "quantity": 1}]
    if payload.plan == "team":
        # A tenant may already have more members than the plan's included
        # seat count (invited teammates while on Free/Pro, or downgraded
        # and re-upgraded) — start the seat line item at the real quantity
        # from the first Checkout session rather than creating it a moment
        # later via sync_seat_quantity's subscription_items.create path.
        member_count = await db.scalar(
            select(func.count(User.id)).where(
                User.tenant_id == tenant.id, User.is_active.is_(True)
            )
        )
        extra_seats = max(0, (member_count or 0) - settings.TEAM_INCLUDED_SEATS)
        if extra_seats > 0:
            line_items.append(
                {"price": settings.STRIPE_PRICE_ID_TEAM_SEAT, "quantity": extra_seats}
            )

    session = client.v1.checkout.sessions.create(
        params={
            "mode": "subscription",
            "customer": customer_id,
            "line_items": line_items,
            "success_url": f"{settings.FRONTEND_BASE_URL}/settings/billing?checkout=success",
            "cancel_url": f"{settings.FRONTEND_BASE_URL}/settings/billing?checkout=cancelled",
            "metadata": {"opengrow_tenant_id": str(tenant.id), "opengrow_plan": payload.plan},
        }
    )
    return CheckoutOut(checkout_url=session.url)


@router.post("/topup", response_model=CheckoutOut)
async def create_topup_checkout(
    payload: TopupRequest,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """One-time Checkout Session for a purchased credit top-up. Paid tiers
    only — free tier isn't credit-gated at all, so buying credit it can't
    spend would be pointless friction, not a real purchase."""
    await _assert_tenant_admin(current)
    if payload.amount_eur_cents not in TOPUP_TIERS_EUR_CENTS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"amount_eur_cents must be one of {TOPUP_TIERS_EUR_CENTS}",
        )

    client = _client()
    tenant = await db.get(Tenant, current.tenant_id)
    if tenant.billing_plan not in ("pro", "team"):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Credit top-ups require a paid plan"
        )
    customer_id = await _get_or_create_stripe_customer(db, client, tenant, current)

    session = client.v1.checkout.sessions.create(
        params={
            "mode": "payment",
            "customer": customer_id,
            "line_items": [
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {"name": "OpenGrow credit top-up"},
                        "unit_amount": payload.amount_eur_cents,
                    },
                    "quantity": 1,
                }
            ],
            "success_url": f"{settings.FRONTEND_BASE_URL}/settings/billing?topup=success",
            "cancel_url": f"{settings.FRONTEND_BASE_URL}/settings/billing?topup=cancelled",
            "metadata": {
                "opengrow_tenant_id": str(tenant.id),
                "opengrow_kind": "credit_topup",
                "opengrow_amount_eur_cents": str(payload.amount_eur_cents),
            },
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
    meta = session.get("metadata") or {}
    tenant_id = meta.get("opengrow_tenant_id")
    if not tenant_id:
        return
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return

    if meta.get("opengrow_kind") == "credit_topup":
        # payment_status guards against a Checkout Session completing for a
        # $0 or deferred-payment edge case — only a genuinely paid session
        # should ever grant purchased credit.
        if session.get("payment_status") != "paid":
            return
        amount_eur_cents = int(meta.get("opengrow_amount_eur_cents", 0))
        if amount_eur_cents <= 0:
            return
        await grant_credits(
            db,
            tenant_id=tenant.id,
            amount_cents=topup_credit_cents(amount_eur_cents),
        )
        return

    plan = meta.get("opengrow_plan", "pro")
    tenant.billing_plan = plan
    await db.commit()


def _find_item(sub: dict, price_id: str) -> dict | None:
    for item in sub["items"]["data"]:
        if item["price"]["id"] == price_id:
            return item
    return None


async def _upsert_subscription(db: AsyncSession, sub: dict) -> None:
    tenant = await _tenant_by_stripe_customer(db, sub["customer"])
    if tenant is None:
        return
    status_value = _STRIPE_STATUS_MAP.get(sub["status"], SubscriptionStatus.INCOMPLETE)

    # A Team subscription carries two line items (base + seat overage); a
    # Pro subscription carries one. Find the BASE plan item specifically
    # rather than assuming items.data[0] — Stripe doesn't guarantee item
    # order, and blindly taking index 0 would misread a Team subscription
    # whose seat item happened to sort first.
    team_item = _find_item(sub, settings.STRIPE_PRICE_ID_TEAM)
    pro_item = _find_item(sub, settings.STRIPE_PRICE_ID_PRO)
    item = team_item or pro_item or sub["items"]["data"][0]
    price_id = item["price"]["id"]
    plan = "team" if team_item else "pro"

    seat_item = _find_item(sub, settings.STRIPE_PRICE_ID_TEAM_SEAT)

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
        if seat_item:
            existing.stripe_seat_item_id = seat_item["id"]
            existing.extra_seats = seat_item["quantity"]
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
                stripe_seat_item_id=seat_item["id"] if seat_item else None,
                extra_seats=seat_item["quantity"] if seat_item else 0,
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


async def sync_seat_quantity(db: AsyncSession, tenant_id, member_count: int) -> None:
    """Push the tenant's real member count to Stripe as the seat-overage
    line item's quantity. Called after a Team tenant's membership changes
    (invite accepted, member removed) — not on every read, so billing
    reflects actual headcount without polling Stripe.

    A no-op for tenants with no active Team subscription (free/Pro tenants,
    or a Team tenant that hasn't completed Checkout yet) — there is nothing
    in Stripe to update yet, and the first Checkout session will establish
    the seat item at the current quantity via the initial line item.
    """
    if not settings.STRIPE_SECRET_KEY:
        return  # billing not configured (e.g. local lite/dev) — nothing to sync

    sub = await db.scalar(
        select(Subscription).where(
            Subscription.tenant_id == tenant_id,
            Subscription.plan == "team",
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.is_deleted.is_(False),
        )
    )
    if sub is None:
        return

    extra_seats = max(0, member_count - settings.TEAM_INCLUDED_SEATS)
    if extra_seats == sub.extra_seats:
        return  # already in sync — avoid a needless Stripe call

    client = _client()
    if sub.stripe_seat_item_id:
        if extra_seats == 0:
            client.v1.subscription_items.delete(sub.stripe_seat_item_id)
            sub.stripe_seat_item_id = None
        else:
            client.v1.subscription_items.update(
                sub.stripe_seat_item_id, params={"quantity": extra_seats}
            )
    elif extra_seats > 0:
        item = client.v1.subscription_items.create(
            params={
                "subscription": sub.stripe_subscription_id,
                "price": settings.STRIPE_PRICE_ID_TEAM_SEAT,
                "quantity": extra_seats,
            }
        )
        sub.stripe_seat_item_id = item.id

    sub.extra_seats = extra_seats
    await db.commit()

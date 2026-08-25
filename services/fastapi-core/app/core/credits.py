"""Prepaid credit balance — atomic check-and-debit for metered actions.

Deliberately hard-stop, not silent overage billing: if a tenant's balance
can't cover an action's cost, the action is rejected with a clear error.
No automatic Stripe charge is ever triggered from here.

Cost is real-usage-based (LiteLLM's maintained per-model price table), not a
flat guessed fee, and never restricted to cheap models — see hold_generation_cost
/ settle_generation_cost for the two-step hold-and-settle flow: a worst-case
estimate is held (and is the actual hard-stop point) before the LLM call, then
reconciled to the real cost — computed from actual token usage — afterward.
Billing strictly after the call would let an empty-balance tenant keep
triggering real-money API calls with nothing to collect against.
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

# Monthly plan grants (cents), credited on each billing-period renewal.
# Pro: 1,000 generations/mo included; Team: 5,000/mo (BUILD-PLAN.md tier
# table) — priced at a representative ~5c/generation for grant sizing only;
# actual per-generation debits are real-usage-based (see below), not this.
PLAN_MONTHLY_GRANT_CENTS = {
    "pro": 1_000 * 5,
    "team": 5_000 * 5,
}

# Purchased credit top-ups (EUR, matching Stripe account currency). The
# monthly plan grant above already runs near-100% margin against real LLM
# cost for a typical tenant (measured ~0.2c/generation on gpt-4o-mini) — a
# tenant buying a top-up has, by definition, already burned through that
# generous included allowance, so top-ups carry their own 25% margin rather
# than passing the purchase through at cost. Fixed tiers (not a free-form
# amount) to keep the Checkout flow and abuse surface simple.
TOPUP_TIERS_EUR_CENTS = [1_000, 2_500, 5_000]  # €10 / €25 / €50
TOPUP_MARKUP = 0.25  # 25% — €1 paid buys 80 credit-cents, not 100


def topup_credit_cents(amount_eur_cents: int) -> int:
    """Credit granted for a top-up of `amount_eur_cents` actually paid."""
    return round(amount_eur_cents * (1 - TOPUP_MARKUP))


class InsufficientCreditsError(HTTPException):
    def __init__(self, cost_cents: int, balance_cents: int):
        super().__init__(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Insufficient credits: this action costs {cost_cents}c, "
            f"balance is {balance_cents}c. Top up in Settings → Billing.",
        )


def estimate_generation_cost_cents(
    *, model: str, messages: list[dict], max_tokens: int
) -> int:
    """Worst-case cost estimate for a not-yet-run generation, in cents.

    Uses the real input token count (litellm.token_counter, no API call) and
    the generation's max_tokens cap as the worst-case output size, priced at
    the specific model's real per-token rate (litellm.cost_per_token) — not
    a flat guess, and not restricted to any particular model.
    """
    import litellm

    prompt_tokens = litellm.token_counter(model=model, messages=messages)
    prompt_cost, completion_cost = litellm.cost_per_token(
        model=model, prompt_tokens=prompt_tokens, completion_tokens=max_tokens
    )
    dollars = prompt_cost + completion_cost
    # Round up to the next whole cent: the hold must never be less than the
    # true worst case (a floor/round-to-nearest could hold too little).
    return max(1, math.ceil(dollars * 100))


def real_generation_cost_cents(completion_response) -> int:
    """Actual cost of a completed generation, in cents, from the real
    response's token usage (litellm.completion_cost)."""
    import litellm

    dollars = litellm.completion_cost(completion_response=completion_response)
    return max(0, round(dollars * 100))


async def debit_credits(db: AsyncSession, *, tenant_id: UUID, cost_cents: int) -> int:
    """Atomically debit `cost_cents` from the tenant's balance if sufficient.

    Uses a single conditional UPDATE (not read-then-write) so concurrent
    requests can't both pass a Python-side balance check against the same
    stale read and jointly overdraw the balance. Returns the new balance.
    Raises InsufficientCreditsError (402) if the balance can't cover it.
    """
    if cost_cents <= 0:
        raise ValueError("cost_cents must be positive")

    result = await db.execute(
        update(Tenant)
        .where(
            Tenant.id == tenant_id,
            Tenant.credit_balance_cents >= cost_cents,
        )
        .values(credit_balance_cents=Tenant.credit_balance_cents - cost_cents)
        .returning(Tenant.credit_balance_cents)
    )
    row = result.first()
    if row is None:
        current = await db.get(Tenant, tenant_id)
        raise InsufficientCreditsError(
            cost_cents, current.credit_balance_cents if current else 0
        )
    await db.commit()
    return row[0]


async def grant_credits(db: AsyncSession, *, tenant_id: UUID, amount_cents: int) -> int:
    """Add `amount_cents` to the tenant's balance (plan grant or top-up)."""
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")

    result = await db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id)
        .values(credit_balance_cents=Tenant.credit_balance_cents + amount_cents)
        .returning(Tenant.credit_balance_cents)
    )
    row = result.first()
    await db.commit()
    return row[0] if row else 0


def debit_credits_sync(db, *, tenant_id: UUID, cost_cents: int) -> int:
    """Sync twin of debit_credits for the Celery worker's plain Session."""
    if cost_cents <= 0:
        raise ValueError("cost_cents must be positive")

    result = db.execute(
        update(Tenant)
        .where(
            Tenant.id == tenant_id,
            Tenant.credit_balance_cents >= cost_cents,
        )
        .values(credit_balance_cents=Tenant.credit_balance_cents - cost_cents)
        .returning(Tenant.credit_balance_cents)
    )
    row = result.first()
    if row is None:
        current = db.get(Tenant, tenant_id)
        raise InsufficientCreditsError(
            cost_cents, current.credit_balance_cents if current else 0
        )
    db.commit()
    return row[0]


def grant_credits_sync(db, *, tenant_id: UUID, amount_cents: int) -> int:
    """Sync twin of grant_credits for the Celery worker's plain Session."""
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")

    result = db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id)
        .values(credit_balance_cents=Tenant.credit_balance_cents + amount_cents)
        .returning(Tenant.credit_balance_cents)
    )
    row = result.first()
    db.commit()
    return row[0] if row else 0

"""Prepaid credit balance — atomic check-and-debit for metered actions.

Deliberately hard-stop, not silent overage billing: if a tenant's balance
can't cover an action's cost, the action is rejected with a clear error.
No automatic Stripe charge is ever triggered from here.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

# Per-action costs (cents), matching the documented Pro rate (€0.05/gen).
GENERATION_COST_CENTS = 5

# Monthly plan grants (cents), credited on each billing-period renewal.
# Pro: 1,000 generations/mo included = 1,000 * GENERATION_COST_CENTS.
PLAN_MONTHLY_GRANT_CENTS = {
    "pro": 1_000 * GENERATION_COST_CENTS,
    "team": 5_000 * GENERATION_COST_CENTS,
}


class InsufficientCreditsError(HTTPException):
    def __init__(self, cost_cents: int, balance_cents: int):
        super().__init__(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Insufficient credits: this action costs {cost_cents}c, "
            f"balance is {balance_cents}c. Top up in Settings → Billing.",
        )


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

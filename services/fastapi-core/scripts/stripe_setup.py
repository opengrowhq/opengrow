"""One-time setup: create the Pro/Team Stripe Products + Prices via the API.

Run once per Stripe account (test or live). Idempotent by the `opengrow_plan`
metadata tag (not name alone) — this account is shared with other, unrelated
projects, so every object this script touches must be unambiguously
identifiable as OpenGrow's before we key off it. Prints the price IDs to
paste into STRIPE_PRICE_ID_PRO / STRIPE_PRICE_ID_TEAM.

Usage: python -m scripts.stripe_setup
"""

import stripe

from app.config import settings

_PLANS = [
    {
        "plan_key": "pro",
        "name": "OpenGrow Pro",
        "env_var": "STRIPE_PRICE_ID_PRO",
        "unit_amount": 2900,  # EUR cents
        "interval": "month",
    },
    {
        "plan_key": "team",
        "name": "OpenGrow Team",
        "env_var": "STRIPE_PRICE_ID_TEAM",
        "unit_amount": 7900,
        "interval": "month",
    },
    {
        # Second line item on a Team subscription, billed per seat beyond
        # the plan's included headcount (settings.TEAM_INCLUDED_SEATS) —
        # not a standalone plan a tenant can subscribe to directly.
        "plan_key": "team_seat",
        "name": "OpenGrow Team — additional seat",
        "env_var": "STRIPE_PRICE_ID_TEAM_SEAT",
        "unit_amount": 1500,
        "interval": "month",
    },
]


def _find_or_create_product(
    client: stripe.StripeClient, name: str, plan_key: str
) -> str:
    # List + client-side filter on the opengrow_plan metadata tag, not the
    # Search API (its index lags live writes by up to ~1 minute — bit us
    # with a duplicate on a quick re-run) and not name alone (this Stripe
    # account is shared with other, unrelated projects/products).
    for product in client.v1.products.list(params={"active": True, "limit": 100}):
        if (
            "opengrow_plan" in product.metadata
            and product.metadata["opengrow_plan"] == plan_key
        ):
            return product.id
    product = client.v1.products.create(
        params={"name": name, "metadata": {"opengrow_plan": plan_key}}
    )
    return product.id


def _find_or_create_price(
    client: stripe.StripeClient,
    product_id: str,
    plan_key: str,
    unit_amount: int,
    interval: str,
) -> str:
    prices = client.v1.prices.list(params={"product": product_id, "active": True})
    for price in prices.data:
        if (
            "opengrow_plan" in price.metadata
            and price.metadata["opengrow_plan"] == plan_key
        ):
            return price.id
    price = client.v1.prices.create(
        params={
            "product": product_id,
            "unit_amount": unit_amount,
            "currency": "eur",
            "recurring": {"interval": interval},
            "metadata": {"opengrow_plan": plan_key},
        }
    )
    return price.id


def main() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise SystemExit("STRIPE_SECRET_KEY is not set — add it to .env first")

    client = stripe.StripeClient(settings.STRIPE_SECRET_KEY)
    print(f"Using Stripe key: {settings.STRIPE_SECRET_KEY[:12]}...")

    for plan in _PLANS:
        product_id = _find_or_create_product(client, plan["name"], plan["plan_key"])
        price_id = _find_or_create_price(
            client, product_id, plan["plan_key"], plan["unit_amount"], plan["interval"]
        )
        print(f"{plan['name']}: product={product_id} price={price_id}")
        print(f"  → set {plan['env_var']}={price_id} in .env")


if __name__ == "__main__":
    main()

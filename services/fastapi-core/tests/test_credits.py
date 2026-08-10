"""Unit tests for real-usage cost estimation (no DB, no API calls)."""

import pytest

from app.core.credits import (
    PLAN_MONTHLY_GRANT_CENTS,
    estimate_generation_cost_cents,
    real_generation_cost_cents,
)

_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Write a short article about blogging for founders."},
]


def test_plan_monthly_grants_match_documented_included_generations():
    # Pro: 1,000 generations/mo included; Team: 5,000/mo (BUILD-PLAN.md).
    # Grant sizing uses a representative 5c/generation; actual per-generation
    # billing is real-usage-based, not this flat rate.
    assert PLAN_MONTHLY_GRANT_CENTS["pro"] == 1_000 * 5
    assert PLAN_MONTHLY_GRANT_CENTS["team"] == 5_000 * 5


def test_estimate_uses_real_per_model_pricing_not_a_flat_rate():
    cheap = estimate_generation_cost_cents(
        model="gpt-4o-mini", messages=_MESSAGES, max_tokens=2000
    )
    expensive = estimate_generation_cost_cents(
        model="gpt-4o", messages=_MESSAGES, max_tokens=2000
    )
    # Same messages/max_tokens, different model — must not collapse to one
    # flat number; the more expensive model must estimate higher.
    assert expensive > cheap


def test_estimate_is_never_zero_even_for_a_tiny_request():
    cents = estimate_generation_cost_cents(
        model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}], max_tokens=1
    )
    assert cents >= 1


def test_estimate_rounds_up_to_the_next_cent():
    # A cheap model + small max_tokens will price to a fraction of a cent —
    # the hold must round UP (never hold less than the true worst case).
    cents = estimate_generation_cost_cents(
        model="gpt-4o-mini", messages=_MESSAGES, max_tokens=1
    )
    assert isinstance(cents, int) and cents >= 1


def test_real_cost_reads_usage_from_a_plain_dict():
    # A large enough usage to round to a non-zero cent amount, so this also
    # exercises the actual rounding, not just "didn't crash".
    resp = {
        "model": "gpt-4o",
        "usage": {
            "prompt_tokens": 100_000,
            "completion_tokens": 100_000,
            "total_tokens": 200_000,
        },
        "choices": [],
    }
    cents = real_generation_cost_cents(resp)
    assert cents > 0


def test_real_cost_rounds_tiny_amounts_to_zero_not_negative():
    resp = {
        "model": "gpt-4o-mini",
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        "choices": [],
    }
    cents = real_generation_cost_cents(resp)
    assert cents == 0

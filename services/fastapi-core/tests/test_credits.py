"""Unit tests for the credit-balance constants and validation."""

import pytest

from app.core.credits import GENERATION_COST_CENTS, PLAN_MONTHLY_GRANT_CENTS


def test_generation_cost_matches_documented_pro_rate():
    assert GENERATION_COST_CENTS == 5


def test_plan_monthly_grants_match_documented_included_generations():
    # Pro: 1,000 generations/mo included; Team: 5,000/mo (BUILD-PLAN.md).
    assert PLAN_MONTHLY_GRANT_CENTS["pro"] == 1_000 * GENERATION_COST_CENTS
    assert PLAN_MONTHLY_GRANT_CENTS["team"] == 5_000 * GENERATION_COST_CENTS

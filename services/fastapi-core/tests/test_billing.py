"""Unit tests for billing status mapping."""

from app.models.subscription import SubscriptionStatus
from app.routers.billing import _STRIPE_STATUS_MAP


def test_stripe_status_map_covers_every_enum_value():
    assert set(_STRIPE_STATUS_MAP.values()) == set(SubscriptionStatus)


def test_stripe_status_map_keys_are_stripe_lowercase_values():
    assert _STRIPE_STATUS_MAP["active"] == SubscriptionStatus.ACTIVE
    assert _STRIPE_STATUS_MAP["past_due"] == SubscriptionStatus.PAST_DUE
    assert _STRIPE_STATUS_MAP["canceled"] == SubscriptionStatus.CANCELED

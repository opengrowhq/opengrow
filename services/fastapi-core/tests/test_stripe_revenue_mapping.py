"""Unit tests for app.routers.analytics._stripe_charge_to_revenue_event —
pure mapping from a Stripe charge object to a RevenueEvent, no DB/network."""

import uuid

from app.models.analytics import RevenueEventType
from app.routers.analytics import _stripe_charge_to_revenue_event

TENANT_ID = uuid.uuid4()
OWNER_ID = uuid.uuid4()


def _charge(**overrides):
    base = {
        "id": "ch_test_123",
        "amount_received": 5000,
        "currency": "usd",
        "created": 1_700_000_000,
        "paid": True,
        "metadata": {},
    }
    base.update(overrides)
    return base


def test_maps_basic_charge_fields():
    ev = _stripe_charge_to_revenue_event(TENANT_ID, OWNER_ID, _charge())

    assert ev.tenant_id == TENANT_ID
    assert ev.owner_id == OWNER_ID
    assert ev.event_type == RevenueEventType.REVENUE
    assert ev.amount_cents == 5000
    assert ev.currency == "USD"
    assert ev.provider == "stripe"
    assert ev.metadata_json == {"stripe_charge_id": "ch_test_123"}


def test_extracts_content_piece_id_from_metadata():
    content_id = uuid.uuid4()
    ev = _stripe_charge_to_revenue_event(
        TENANT_ID, OWNER_ID, _charge(metadata={"content_piece_id": str(content_id)})
    )
    assert ev.content_piece_id == content_id


def test_ignores_invalid_content_piece_id():
    ev = _stripe_charge_to_revenue_event(
        TENANT_ID, OWNER_ID, _charge(metadata={"content_piece_id": "not-a-uuid"})
    )
    assert ev.content_piece_id is None


def test_extracts_source_url_from_metadata():
    ev = _stripe_charge_to_revenue_event(
        TENANT_ID,
        OWNER_ID,
        _charge(metadata={"source_url": "https://example.com/blog/post"}),
    )
    assert ev.source_url == "https://example.com/blog/post"


def test_dedupe_key_is_stable_for_the_same_charge():
    a = _stripe_charge_to_revenue_event(TENANT_ID, OWNER_ID, _charge())
    b = _stripe_charge_to_revenue_event(TENANT_ID, OWNER_ID, _charge())
    assert a.dedupe_key == b.dedupe_key


def test_dedupe_key_differs_for_different_charges():
    a = _stripe_charge_to_revenue_event(TENANT_ID, OWNER_ID, _charge(id="ch_a"))
    b = _stripe_charge_to_revenue_event(TENANT_ID, OWNER_ID, _charge(id="ch_b"))
    assert a.dedupe_key != b.dedupe_key


def test_occurred_at_derived_from_charge_created():
    ev = _stripe_charge_to_revenue_event(
        TENANT_ID, OWNER_ID, _charge(created=1_700_000_000)
    )
    assert ev.occurred_at.timestamp() == 1_700_000_000


def test_currency_normalized_uppercase():
    ev = _stripe_charge_to_revenue_event(TENANT_ID, OWNER_ID, _charge(currency="eur"))
    assert ev.currency == "EUR"

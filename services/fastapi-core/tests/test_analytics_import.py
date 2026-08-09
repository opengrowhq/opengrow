from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.analytics_import import event_dedupe_key, normalize_channel
from app.routers.analytics import _csv_row_to_import_row


def test_normalize_channel_prefers_explicit_value():
    assert (
        normalize_channel("ga4", "https://google.com/search", "Paid Search")
        == "paid_search"
    )


def test_normalize_channel_infers_known_source_hosts():
    assert (
        normalize_channel("manual", "https://www.linkedin.com/company/opengrow", None)
        == "social"
    )
    assert (
        normalize_channel("manual", "https://www.google.com/search?q=opengrow", None)
        == "search"
    )


def test_normalize_channel_falls_back_to_provider():
    assert normalize_channel("gsc", None, None) == "search"
    assert normalize_channel("ga4", None, None) == "analytics"


def test_event_dedupe_key_is_stable_for_same_daily_window():
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    content_id = UUID("00000000-0000-0000-0000-000000000002")
    first = event_dedupe_key(
        tenant_id=tenant_id,
        provider="ga4",
        event_type="VISIT",
        content_piece_id=content_id,
        source_url="https://example.test/Page",
        occurred_at=datetime(2026, 7, 22, 10, tzinfo=timezone.utc),
        external_id=None,
    )
    second = event_dedupe_key(
        tenant_id=tenant_id,
        provider="ga4",
        event_type="VISIT",
        content_piece_id=content_id,
        source_url="https://example.test/page",
        occurred_at=datetime(2026, 7, 22, 23, tzinfo=timezone.utc),
        external_id=None,
    )

    assert first == second


def test_csv_row_to_import_row_parses_populated_fields():
    row = _csv_row_to_import_row(
        {
            "source_url": "https://example.test/post",
            "channel": "newsletter",
            "visits": "12",
            "signups": "3",
            "revenue_cents": "4500",
            "currency": "usd",
            "occurred_at": "2026-08-01T00:00:00Z",
        }
    )
    assert row.source_url == "https://example.test/post"
    assert row.channel == "newsletter"
    assert row.visits == 12
    assert row.signups == 3
    assert row.revenue_cents == 4500
    assert row.currency == "USD"
    assert row.occurred_at is not None


def test_csv_row_to_import_row_treats_blank_cells_as_absent():
    row = _csv_row_to_import_row(
        {
            "source_url": "",
            "visits": "",
            "revenue_cents": None,
        }
    )
    assert row.source_url is None
    assert row.visits == 0
    assert row.revenue_cents == 0


def test_csv_row_to_import_row_rejects_negative_counts():
    with pytest.raises(ValidationError):
        _csv_row_to_import_row({"visits": "-1"})


def test_csv_row_to_import_row_rejects_non_integer_counts():
    with pytest.raises(ValueError):
        _csv_row_to_import_row({"visits": "not-a-number"})


def test_event_dedupe_key_uses_external_id_when_present():
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    first = event_dedupe_key(
        tenant_id=tenant_id,
        provider="gsc",
        event_type="VISIT",
        content_piece_id=None,
        source_url="https://example.test/a",
        occurred_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
        external_id="row-1",
    )
    second = event_dedupe_key(
        tenant_id=tenant_id,
        provider="gsc",
        event_type="VISIT",
        content_piece_id=None,
        source_url="https://example.test/b",
        occurred_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
        external_id="row-1",
    )

    assert first == second

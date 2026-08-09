from datetime import datetime, timezone
from uuid import UUID

from app.core.analytics_import import event_dedupe_key, normalize_channel


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

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.analytics import (
    AnalyticsConnectorAuthUrlOut,
    AnalyticsConnectorCallback,
    AnalyticsConnectorCreate,
    AnalyticsConnectorSyncOut,
    AnalyticsImportRequest,
    AttributionDeltaOut,
    AttributionSummaryOut,
    AttributionTrendOut,
    ChannelTrendOut,
    ContentTrendOut,
    PublicTrackEvent,
    PublicTrackOut,
    RevenueEventCreate,
    SourceTrendOut,
    TrackingStatusOut,
)


def test_revenue_event_create_normalizes_values():
    event = RevenueEventCreate(
        event_type=" revenue ",
        event_count=3,
        amount_cents=1299,
        currency="eur",
        occurred_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
    )

    assert event.event_type == "REVENUE"
    assert event.currency == "EUR"
    assert event.event_count == 3
    assert event.amount_cents == 1299


@pytest.mark.parametrize("event_count", [0, -1])
def test_revenue_event_create_rejects_invalid_event_count(event_count):
    with pytest.raises(ValidationError):
        RevenueEventCreate(event_type="VISIT", event_count=event_count)


def test_revenue_event_create_rejects_negative_amount():
    with pytest.raises(ValidationError):
        RevenueEventCreate(event_type="REVENUE", amount_cents=-1)


@pytest.mark.parametrize("currency", ["", "US", "USDD", "12$"])
def test_revenue_event_create_rejects_invalid_currency(currency):
    with pytest.raises(ValidationError):
        RevenueEventCreate(event_type="SIGNUP", currency=currency)


def test_analytics_import_request_accepts_aggregate_rows():
    request = AnalyticsImportRequest(
        provider="ga4",
        rows=[
            {
                "content_piece_id": "content-1",
                "source_url": "https://example.test/landing",
                "channel": "organic_search",
                "external_id": "ga4-row-1",
                "visits": 10,
                "leads": 2,
                "customers": 1,
                "revenue_cents": 129900,
                "currency": "eur",
            }
        ],
    )

    assert request.provider == "ga4"
    assert request.rows[0].visits == 10
    assert request.rows[0].channel == "organic_search"
    assert request.rows[0].external_id == "ga4-row-1"
    assert request.rows[0].currency == "EUR"


def test_analytics_import_request_rejects_invalid_provider():
    with pytest.raises(ValidationError):
        AnalyticsImportRequest(provider="csv", rows=[{"visits": 1}])


def test_analytics_import_request_rejects_empty_rows():
    with pytest.raises(ValidationError):
        AnalyticsImportRequest(provider="manual", rows=[])


def test_analytics_connector_create_accepts_google_providers():
    connector = AnalyticsConnectorCreate(
        provider="gsc",
        display_name="Search Console",
        site_url="https://example.test",
    )

    assert connector.provider == "gsc"
    assert connector.display_name == "Search Console"


def test_analytics_connector_create_rejects_unknown_provider():
    with pytest.raises(ValidationError):
        AnalyticsConnectorCreate(provider="matomo", display_name="Matomo")


def test_analytics_connector_auth_url_out_can_report_unconfigured_state():
    out = AnalyticsConnectorAuthUrlOut(
        configured=False,
        provider="ga4",
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        message="missing config",
    )

    assert out.auth_url is None
    assert out.state is None
    assert out.configured is False


def test_analytics_connector_callback_requires_code():
    callback = AnalyticsConnectorCallback(code="oauth-code", state="oauth-state")
    assert callback.code == "oauth-code"
    with pytest.raises(ValidationError):
        AnalyticsConnectorCallback(code="")
    with pytest.raises(ValidationError):
        AnalyticsConnectorCallback(code="oauth-code")  # state is required
    with pytest.raises(ValidationError):
        AnalyticsConnectorCallback(code="oauth-code", state="")


def test_analytics_connector_sync_out_reports_queued_task():
    out = AnalyticsConnectorSyncOut(
        connector_id="connector-1",
        task_id="task-1",
        status="QUEUED",
    )

    assert out.connector_id == "connector-1"
    assert out.task_id == "task-1"
    assert out.status == "QUEUED"


def test_public_track_event_normalizes_conversion():
    event = PublicTrackEvent(
        tenant_slug="demo",
        event_type="revenue",
        amount_cents=4900,
        currency="eur",
        external_id="order-1",
    )

    assert event.event_type == "REVENUE"
    assert event.currency == "EUR"
    assert event.amount_cents == 4900


def test_public_track_event_rejects_visit_payload():
    with pytest.raises(ValidationError):
        PublicTrackEvent(tenant_slug="demo", event_type="visit")


def test_public_track_out_reports_event_id():
    out = PublicTrackOut(ok=True, event_id="event-1")

    assert out.ok is True
    assert out.event_id == "event-1"


def test_tracking_status_out_reports_install_state():
    out = TrackingStatusOut(
        installed=True,
        events=3,
        first_party_visits=2,
        first_party_conversions=1,
        last_seen_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
    )

    assert out.installed is True
    assert out.events == 3
    assert out.first_party_visits == 2
    assert out.first_party_conversions == 1


def test_attribution_trend_out_reports_current_previous_and_delta():
    out = AttributionTrendOut(
        days=30,
        current=AttributionSummaryOut(
            events=10,
            visits=6,
            signups=2,
            leads=1,
            customers=1,
            revenue_cents=10000,
        ),
        previous=AttributionSummaryOut(
            events=5,
            visits=3,
            signups=1,
            leads=1,
            customers=0,
            revenue_cents=0,
        ),
        deltas={"revenue_cents": AttributionDeltaOut(absolute=10000, percent=None)},
    )

    assert out.days == 30
    assert out.current.events == 10
    assert out.previous.events == 5
    assert out.deltas["revenue_cents"].absolute == 10000


def test_channel_trend_out_reports_channel_delta():
    out = ChannelTrendOut(
        channel="organic_search",
        current=AttributionSummaryOut(
            events=4,
            visits=3,
            signups=0,
            leads=1,
            customers=0,
            revenue_cents=0,
        ),
        previous=AttributionSummaryOut(
            events=2,
            visits=2,
            signups=0,
            leads=0,
            customers=0,
            revenue_cents=0,
        ),
        deltas={"leads": AttributionDeltaOut(absolute=1, percent=None)},
    )

    assert out.channel == "organic_search"
    assert out.current.leads == 1
    assert out.deltas["leads"].absolute == 1


def test_source_trend_out_reports_source_delta():
    out = SourceTrendOut(
        source_url="https://example.test/landing",
        current=AttributionSummaryOut(
            events=2,
            visits=1,
            signups=0,
            leads=1,
            customers=0,
            revenue_cents=0,
        ),
        previous=AttributionSummaryOut(
            events=1,
            visits=1,
            signups=0,
            leads=0,
            customers=0,
            revenue_cents=0,
        ),
        deltas={"events": AttributionDeltaOut(absolute=1, percent=100)},
    )

    assert out.source_url == "https://example.test/landing"
    assert out.deltas["events"].percent == 100


def test_content_trend_out_reports_content_metadata():
    out = ContentTrendOut(
        content_piece_id="content-1",
        title="Launch page",
        status="PUBLISHED",
        current=AttributionSummaryOut(
            events=3,
            visits=2,
            signups=0,
            leads=1,
            customers=0,
            revenue_cents=0,
        ),
        previous=AttributionSummaryOut(
            events=0,
            visits=0,
            signups=0,
            leads=0,
            customers=0,
            revenue_cents=0,
        ),
        deltas={"leads": AttributionDeltaOut(absolute=1, percent=None)},
    )

    assert out.title == "Launch page"
    assert out.status == "PUBLISHED"
    assert out.current.events == 3

from datetime import date

from app.core.google_analytics import (
    build_ga4_request,
    build_gsc_request,
    default_sync_window,
    map_ga4_rows,
    map_gsc_rows,
)


def test_default_sync_window_uses_previous_seven_complete_days():
    start, end = default_sync_window(date(2026, 7, 22))

    assert start == date(2026, 7, 15)
    assert end == date(2026, 7, 21)


def test_build_gsc_request_groups_by_page():
    request = build_gsc_request(date(2026, 7, 1), date(2026, 7, 7), row_limit=10)

    assert request["dimensions"] == ["page"]
    assert request["searchType"] == "web"
    assert request["rowLimit"] == 10


def test_build_ga4_request_uses_landing_page_metrics():
    request = build_ga4_request(date(2026, 7, 1), date(2026, 7, 7), row_limit=10)

    assert request["dimensions"] == [{"name": "landingPagePlusQueryString"}]
    assert request["metrics"] == [
        {"name": "activeUsers"},
        {"name": "conversions"},
        {"name": "totalRevenue"},
    ]
    assert request["limit"] == "10"


def test_map_gsc_rows_to_import_rows():
    rows = map_gsc_rows(
        {
            "rows": [
                {
                    "keys": ["https://example.test/page"],
                    "clicks": 12,
                    "impressions": 100,
                    "ctr": 0.12,
                    "position": 3.5,
                }
            ]
        },
        site_url="https://example.test",
        start=date(2026, 7, 1),
        end=date(2026, 7, 7),
    )

    assert rows[0]["source_url"] == "https://example.test/page"
    assert rows[0]["channel"] == "organic_search"
    assert rows[0]["visits"] == 12
    assert rows[0]["metadata"]["impressions"] == 100


def test_map_ga4_rows_to_import_rows():
    rows = map_ga4_rows(
        {
            "rows": [
                {
                    "dimensionValues": [{"value": "/pricing"}],
                    "metricValues": [
                        {"value": "25"},
                        {"value": "3"},
                        {"value": "19.99"},
                    ],
                }
            ]
        },
        site_url="https://example.test",
        start=date(2026, 7, 1),
        end=date(2026, 7, 7),
    )

    assert rows[0]["source_url"] == "https://example.test/pricing"
    assert rows[0]["channel"] == "analytics"
    assert rows[0]["visits"] == 25
    assert rows[0]["signups"] == 3
    assert rows[0]["revenue_cents"] == 1999

from datetime import datetime, timezone

import pytest

from app.core.analytics_window import analytics_periods, analytics_since, trend_delta


def test_analytics_since_returns_window_start():
    now = datetime(2026, 7, 22, 12, tzinfo=timezone.utc)

    assert analytics_since(7, now) == datetime(2026, 7, 15, 12, tzinfo=timezone.utc)


def test_analytics_since_all_time_returns_none():
    assert analytics_since(None) is None


def test_analytics_periods_returns_previous_and_current_bounds():
    now = datetime(2026, 7, 22, 12, tzinfo=timezone.utc)

    previous_start, current_start, end = analytics_periods(7, now)

    assert previous_start == datetime(2026, 7, 8, 12, tzinfo=timezone.utc)
    assert current_start == datetime(2026, 7, 15, 12, tzinfo=timezone.utc)
    assert end == now


def test_trend_delta_handles_empty_previous_window():
    assert trend_delta(10, 0) == {"absolute": 10, "percent": None}
    assert trend_delta(15, 10) == {"absolute": 5, "percent": 50}


@pytest.mark.parametrize("days", [0, 366])
def test_analytics_since_rejects_out_of_range(days):
    with pytest.raises(ValueError):
        analytics_since(days)


@pytest.mark.parametrize("days", [0, 366])
def test_analytics_periods_rejects_out_of_range(days):
    with pytest.raises(ValueError):
        analytics_periods(days)

from datetime import datetime, timedelta, timezone


def analytics_since(days: int | None, now: datetime | None = None) -> datetime | None:
    if days is None:
        return None
    if days < 1 or days > 365:
        raise ValueError("days must be between 1 and 365")
    anchor = now or datetime.now(timezone.utc)
    return anchor - timedelta(days=days)


def analytics_periods(
    days: int, now: datetime | None = None
) -> tuple[datetime, datetime, datetime]:
    if days < 1 or days > 365:
        raise ValueError("days must be between 1 and 365")
    anchor = now or datetime.now(timezone.utc)
    current_start = anchor - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)
    return previous_start, current_start, anchor


def trend_delta(current: int, previous: int) -> dict[str, int | None]:
    absolute = current - previous
    percent = None if previous == 0 else round((absolute / previous) * 100)
    return {"absolute": absolute, "percent": percent}

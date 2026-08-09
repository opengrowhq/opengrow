from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote, urljoin

import httpx

GSC_SEARCH_ANALYTICS_URL = (
    "https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query"
)
GA4_RUN_REPORT_URL = (
    "https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
)


def default_sync_window(today: date | None = None) -> tuple[date, date]:
    current = today or date.today()
    end = current - timedelta(days=1)
    start = end - timedelta(days=6)
    return start, end


def build_gsc_request(start: date, end: date, row_limit: int = 250) -> dict:
    return {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["page"],
        "searchType": "web",
        "rowLimit": row_limit,
    }


def build_ga4_request(start: date, end: date, row_limit: int = 250) -> dict:
    return {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": "landingPagePlusQueryString"}],
        "metrics": [
            {"name": "activeUsers"},
            {"name": "conversions"},
            {"name": "totalRevenue"},
        ],
        "limit": str(row_limit),
    }


def _absolute_url(site_url: str | None, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    if not site_url:
        return path
    return urljoin(site_url.rstrip("/") + "/", path.lstrip("/"))


def map_gsc_rows(
    response: dict, *, site_url: str, start: date, end: date
) -> list[dict]:
    rows = []
    for item in response.get("rows") or []:
        keys = item.get("keys") or []
        page = keys[0] if keys else site_url
        clicks = int(item.get("clicks") or 0)
        if clicks <= 0:
            continue
        source_url = _absolute_url(site_url, page)
        rows.append(
            {
                "source_url": source_url,
                "channel": "organic_search",
                "visits": clicks,
                "external_id": f"gsc:{site_url}:{start.isoformat()}:{end.isoformat()}:{source_url}",
                "metadata": {
                    "impressions": int(item.get("impressions") or 0),
                    "ctr": item.get("ctr"),
                    "position": item.get("position"),
                },
            }
        )
    return rows


def map_ga4_rows(
    response: dict, *, site_url: str | None, start: date, end: date
) -> list[dict]:
    rows = []
    for item in response.get("rows") or []:
        dimensions = item.get("dimensionValues") or []
        metrics = item.get("metricValues") or []
        path = dimensions[0].get("value") if dimensions else "/"
        active_users = (
            int(float(metrics[0].get("value") or 0)) if len(metrics) > 0 else 0
        )
        conversions = (
            int(float(metrics[1].get("value") or 0)) if len(metrics) > 1 else 0
        )
        revenue = float(metrics[2].get("value") or 0) if len(metrics) > 2 else 0.0
        if active_users <= 0 and conversions <= 0 and revenue <= 0:
            continue
        source_url = _absolute_url(site_url, path or "/")
        rows.append(
            {
                "source_url": source_url,
                "channel": "analytics",
                "visits": active_users,
                "signups": conversions,
                "revenue_cents": int(round(revenue * 100)),
                "external_id": f"ga4:{start.isoformat()}:{end.isoformat()}:{source_url}",
                "metadata": {"landing_page": path},
            }
        )
    return rows


async def fetch_gsc_rows(
    *,
    access_token: str,
    site_url: str,
    start: date,
    end: date,
) -> list[dict]:
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        response = await client.post(
            GSC_SEARCH_ANALYTICS_URL.format(site_url=quote(site_url, safe="")),
            json=build_gsc_request(start, end),
            headers={"Authorization": f"Bearer {access_token}"},
        )
    response.raise_for_status()
    return map_gsc_rows(response.json(), site_url=site_url, start=start, end=end)


async def fetch_ga4_rows(
    *,
    access_token: str,
    property_id: str,
    site_url: str | None,
    start: date,
    end: date,
) -> list[dict]:
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        response = await client.post(
            GA4_RUN_REPORT_URL.format(property_id=property_id),
            json=build_ga4_request(start, end),
            headers={"Authorization": f"Bearer {access_token}"},
        )
    response.raise_for_status()
    return map_ga4_rows(response.json(), site_url=site_url, start=start, end=end)

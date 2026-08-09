from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import UUID


CHANNEL_BY_PROVIDER = {
    "ga4": "analytics",
    "gsc": "search",
    "manual": "manual",
}

HOST_CHANNELS = (
    ("google.", "search"),
    ("bing.", "search"),
    ("linkedin.", "social"),
    ("twitter.", "social"),
    ("x.com", "social"),
    ("facebook.", "social"),
    ("instagram.", "social"),
    ("youtube.", "video"),
    ("tiktok.", "video"),
)


def normalize_channel(
    provider: str, source_url: str | None, channel: str | None
) -> str:
    if channel:
        return channel.strip().lower().replace(" ", "_") or "unknown"
    lowered = (source_url or "").lower()
    for needle, value in HOST_CHANNELS:
        if needle in lowered:
            return value
    return CHANNEL_BY_PROVIDER.get(provider, "unknown")


def event_dedupe_key(
    *,
    tenant_id: UUID,
    provider: str,
    event_type: str,
    content_piece_id: UUID | None,
    source_url: str | None,
    occurred_at: datetime,
    external_id: str | None,
) -> str:
    if external_id:
        raw = f"{tenant_id}|{provider}|{event_type}|external|{external_id.strip()}"
    else:
        content_key = str(content_piece_id) if content_piece_id else "unassigned"
        source_key = (source_url or "unknown").strip().lower()
        window_key = occurred_at.date().isoformat()
        raw = f"{tenant_id}|{provider}|{event_type}|{content_key}|{source_key}|{window_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

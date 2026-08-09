from __future__ import annotations

from typing import TypedDict


class PublisherError(Exception):
    """Raised for any non-recoverable failure publishing to a channel."""


class PublishResult(TypedDict):
    url: str
    external_ref: str

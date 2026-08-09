"""Multi-channel publishing adapters.

Each adapter turns an approved ContentPiece into a published post on an external
channel, BYOK (credentials come in the request config). Same spirit as
github_publisher: plain httpx, no per-vendor SDK. See `registry` for dispatch.
"""

from app.core.publishers.base import PublisherError, PublishResult
from app.core.publishers.registry import (
    KNOWN_CHANNELS,
    get_adapter,
    is_implemented,
)

__all__ = [
    "PublisherError",
    "PublishResult",
    "KNOWN_CHANNELS",
    "get_adapter",
    "is_implemented",
]

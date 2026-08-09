"""Channel → adapter dispatch.

Implemented adapters expose `async publish(*, title, body, config) -> PublishResult`.
Known-but-unimplemented channels are advertised (so the API surface + enum exist
for clients to design against) but return 501 until built. GitHub PR has its own
dedicated endpoint and is intentionally not routed through the generic publisher.
"""

from __future__ import annotations

from app.core.publishers import email, ghost, linkedin, webflow, wordpress
from app.core.publishers import x as x_channel

# channel name (matches PublicationChannel) → adapter module
_ADAPTERS = {
    "WORDPRESS": wordpress,
    "GHOST": ghost,
    "WEBFLOW": webflow,
    "EMAIL": email,
    "X": x_channel,
    "LINKEDIN": linkedin,
}

# Advertised generic channels (GITHUB_PR handled by its own endpoint).
KNOWN_CHANNELS = ["WORDPRESS", "GHOST", "WEBFLOW", "X", "LINKEDIN", "EMAIL"]


def is_implemented(channel: str) -> bool:
    return channel in _ADAPTERS


def get_adapter(channel: str):
    return _ADAPTERS.get(channel)

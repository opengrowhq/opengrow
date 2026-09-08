"""Channel → adapter dispatch.

Every known channel has an implemented adapter exposing
`async publish(*, title, body, config) -> PublishResult`. GitHub PR has its
own dedicated endpoint and is intentionally not routed through the generic
publisher.
"""

from __future__ import annotations

from app.core.publishers import email, ghost, linkedin, slack, webflow, wordpress
from app.core.publishers import x as x_channel

# channel name (matches PublicationChannel) → adapter module
_ADAPTERS = {
    "WORDPRESS": wordpress,
    "GHOST": ghost,
    "WEBFLOW": webflow,
    "EMAIL": email,
    "X": x_channel,
    "LINKEDIN": linkedin,
    "SLACK": slack,
}

# Advertised generic channels (GITHUB_PR handled by its own endpoint).
KNOWN_CHANNELS = ["WORDPRESS", "GHOST", "WEBFLOW", "X", "LINKEDIN", "EMAIL", "SLACK"]


def is_implemented(channel: str) -> bool:
    return channel in _ADAPTERS


def get_adapter(channel: str):
    return _ADAPTERS.get(channel)

"""SSRF guards for BYOK publisher targets.

Publisher config carries user-controlled hosts (WordPress site_url, Ghost
admin_api_url, Email smtp_host). Before connecting, validate them against the
same public-IP guard the brand scraper uses, so a tenant can't point a publish
at internal services or the cloud metadata endpoint.
"""

from __future__ import annotations

from app.core.brand_scraper import (
    UnsafeURLError,
    assert_public_host,
    validate_public_http_url,
)
from app.core.publishers.base import PublisherError


def safe_url(url: str) -> None:
    try:
        validate_public_http_url(url)
    except UnsafeURLError as e:
        raise PublisherError(f"Refusing to connect to non-public URL: {e}") from e


def safe_host(host: str, port: int) -> None:
    try:
        assert_public_host(host, int(port))
    except (UnsafeURLError, ValueError) as e:
        raise PublisherError(f"Refusing to connect to non-public host: {e}") from e

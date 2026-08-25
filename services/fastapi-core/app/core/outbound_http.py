"""Shared SSRF-guarded outbound HTTP fetch — the generic guard machinery
factored out of app.core.brand_scraper so any external-endpoint caller
(brand site fetching, keyword-research scraping, …) gets the same
protection without re-deriving it: allow only http/https, resolve and
reject private/loopback/link-local/reserved/metadata IPs, re-validate on
every redirect hop, cap response size and time, pin DNS against a
TOCTOU re-resolution between the check and the actual connect.
"""

from __future__ import annotations

import ipaddress
import socket
from contextlib import contextmanager
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES = 2_000_000  # 2 MB
MAX_REDIRECTS = 3
TIMEOUT_S = 15
USER_AGENT = "OpenGrowBot/0.1 (+https://opengrow.dev)"


class UnsafeURLError(Exception):
    """The URL is not a safe, public http(s) URL."""


def validate_public_http_url(url: str) -> None:
    _resolve_public_http_url(url)


def _is_blocked_ip(ip) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # covers 169.254.x cloud metadata
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_public_host(host: str, port: int) -> None:
    """Raise UnsafeURLError unless `host` resolves only to public IPs.

    Host/port-level guard (no scheme) — for non-HTTP callers like SMTP.
    """
    if not host:
        raise UnsafeURLError("No host")
    try:
        infos = socket.getaddrinfo(host, port)
    except socket.gaierror:
        raise UnsafeURLError("Host does not resolve")
    for info in infos:
        if _is_blocked_ip(ipaddress.ip_address(info[4][0])):
            raise UnsafeURLError("Host resolves to a non-public address")


def _resolve_public_http_url(url: str) -> list[tuple]:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError("URL must be http or https")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL has no host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port)
    except socket.gaierror:
        raise UnsafeURLError("Host does not resolve")

    safe_infos = []
    for info in infos:
        if _is_blocked_ip(ipaddress.ip_address(info[4][0])):
            raise UnsafeURLError("URL resolves to a non-public address")
        safe_infos.append(info)
    return safe_infos


@contextmanager
def _pinned_dns(host: str, port: int, infos: list[tuple]):
    original = socket.getaddrinfo

    def pinned_getaddrinfo(query_host, query_port, *args, **kwargs):
        if query_host == host and int(query_port or port) == port:
            return infos
        return original(query_host, query_port, *args, **kwargs)

    socket.getaddrinfo = pinned_getaddrinfo
    try:
        yield
    finally:
        socket.getaddrinfo = original


def fetch_url(url: str, *, headers: dict | None = None) -> httpx.Response:
    """GET a public URL through the SSRF guards, following redirects
    manually (re-validating each hop) and capping body size. Returns the
    raw httpx.Response with `.content` truncated to MAX_BYTES — callers
    parse it as HTML, JSON, whatever the endpoint returns.
    """
    validate_public_http_url(url)
    current = url
    merged_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    with httpx.Client(
        timeout=TIMEOUT_S,
        follow_redirects=False,
        trust_env=False,
        headers=merged_headers,
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            parsed = urlparse(current)
            host = parsed.hostname
            if not host:
                raise UnsafeURLError("URL has no host")
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            infos = _resolve_public_http_url(current)
            with _pinned_dns(host, port, infos):
                resp = client.get(current)
            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    break
                current = urljoin(current, location)
                validate_public_http_url(current)  # re-guard each hop
                continue
            resp.raise_for_status()
            resp._content = resp.content[:MAX_BYTES]  # truncate in place
            return resp
    raise UnsafeURLError("Too many redirects")

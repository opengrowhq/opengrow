"""Brand DNA site fetching — SSRF-guarded.

Users submit arbitrary URLs, so this is a classic SSRF surface. We:
  - allow only http/https,
  - resolve the host and reject private/loopback/link-local/reserved/metadata IPs,
  - re-validate on every redirect hop (cap the number of hops),
  - cap response size and time.

Text extraction uses the stdlib HTML parser (no extra dependency) — good enough
for a v1 brand profile; a richer extractor can replace `_html_to_text` later.
"""

from __future__ import annotations

import ipaddress
import socket
from contextlib import contextmanager
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES = 2_000_000  # 2 MB
MAX_REDIRECTS = 3
TIMEOUT_S = 15


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


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.chunks: list[str] = []
        self.title: str | None = None
        self.description: str | None = None
        self.theme_color: str | None = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            a = dict(attrs)
            name = (a.get("name") or a.get("property") or "").lower()
            if name in ("description", "og:description") and a.get("content"):
                self.description = self.description or a["content"]
            if name == "theme-color" and a.get("content"):
                self.theme_color = a["content"]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title and not self.title:
            self.title = text
        else:
            self.chunks.append(text)


def _html_to_text(html: str) -> _TextExtractor:
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    return p


def fetch_site(url: str) -> dict:
    """Fetch a public URL safely and return extracted brand signals."""
    validate_public_http_url(url)
    current = url
    with httpx.Client(
        timeout=TIMEOUT_S,
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "OpenGrowBot/0.1 (+https://opengrow.dev)"},
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
            raw = resp.content[:MAX_BYTES]
            html = raw.decode(resp.encoding or "utf-8", errors="ignore")
            ex = _html_to_text(html)
            text = " ".join(ex.chunks)
            return {
                "final_url": current,
                "title": ex.title,
                "description": ex.description,
                "theme_color": ex.theme_color,
                "text": text[:20_000],
            }
    raise UnsafeURLError("Too many redirects")

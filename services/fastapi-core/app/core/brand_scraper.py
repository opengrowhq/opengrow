"""Brand DNA site fetching — SSRF-guarded.

Users submit arbitrary URLs, so this is a classic SSRF surface. The guard
machinery (scheme/host/redirect/size/timeout checks, DNS pinning) lives in
app.core.outbound_http, shared with any other external-endpoint caller
(e.g. the keyword-research scraper) so the SSRF protections aren't
re-derived per caller.

Text extraction uses the stdlib HTML parser (no extra dependency) — good enough
for a v1 brand profile; a richer extractor can replace `_html_to_text` later.
"""

from __future__ import annotations

from html.parser import HTMLParser

from app.core.outbound_http import (
    MAX_BYTES,
    UnsafeURLError,
    assert_public_host,
    fetch_url,
    validate_public_http_url,
)

__all__ = [
    "MAX_BYTES",
    "UnsafeURLError",
    "assert_public_host",
    "fetch_site",
    "validate_public_http_url",
]


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
    resp = fetch_url(url)
    html = resp.content.decode(resp.encoding or "utf-8", errors="ignore")
    ex = _html_to_text(html)
    text = " ".join(ex.chunks)
    return {
        "final_url": str(resp.url),
        "title": ex.title,
        "description": ex.description,
        "theme_color": ex.theme_color,
        "text": text[:20_000],
    }

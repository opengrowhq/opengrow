"""No-API-key keyword research: Google Autocomplete + People Also Ask (PAA)
+ Bing SERP titles, so the orchestrator's article pipeline can turn a bare
topic into a real primary/secondary keyword set without a paid
keyword-research API.

Each source hits a real external endpoint through the shared SSRF-guarded
fetcher (app.core.outbound_http) — same protections as brand-site scraping,
just pointed at Google/Bing instead of a tenant-submitted URL. Best-effort by
source: if one source fails or its response shape changes (scrapers are
inherently brittle against markup/endpoint drift), the others still
contribute, and the caller falls back to the bare topic if every source
fails — this step must never block the pipeline on an external site being
unreachable or having changed its markup.
"""

from __future__ import annotations

import json
import logging
import re
from html.parser import HTMLParser
from urllib.parse import quote_plus

from app.core.outbound_http import fetch_url

log = logging.getLogger(__name__)

AUTOCOMPLETE_URL = (
    "https://suggestqueries.google.com/complete/search?client=firefox&q={q}"
)
BING_SEARCH_URL = "https://www.bing.com/search?q={q}"
MAX_SUGGESTIONS = 10
MAX_PAA_QUESTIONS = 8
MAX_BING_TITLES = 10


def _fetch_autocomplete(topic: str) -> list[str]:
    try:
        resp = fetch_url(AUTOCOMPLETE_URL.format(q=quote_plus(topic)))
        data = json.loads(resp.content.decode("utf-8", errors="ignore"))
        suggestions = data[1] if isinstance(data, list) and len(data) > 1 else []
        return [s for s in suggestions if isinstance(s, str) and s.strip()][
            :MAX_SUGGESTIONS
        ]
    except Exception as e:
        log.info("autocomplete keyword research skipped: %s", e.__class__.__name__)
        return []


class _BingResultExtractor(HTMLParser):
    """Pulls PAA-style question snippets and organic result titles out of a
    Bing SERP. Bing's markup is undocumented and changes over time — this is
    a best-effort heuristic (look for '?'-ending short text nodes for PAA,
    <h2> text for organic titles), not a maintained scraper contract."""

    def __init__(self) -> None:
        super().__init__()
        self._in_h2 = False
        self._h2_text: list[str] = []
        self.titles: list[str] = []
        self.questions: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self._in_h2 = True
            self._h2_text = []

    def handle_endtag(self, tag):
        if tag == "h2" and self._in_h2:
            self._in_h2 = False
            text = " ".join(self._h2_text).strip()
            if text:
                if text.endswith("?") and len(text) <= 150:
                    self.questions.append(text)
                else:
                    self.titles.append(text)

    def handle_data(self, data):
        if self._in_h2:
            text = data.strip()
            if text:
                self._h2_text.append(text)


_QUESTION_RE = re.compile(
    r"^(who|what|when|where|why|how|is|are|can|does|do)\b", re.IGNORECASE
)


def _fetch_bing_serp(topic: str) -> dict:
    try:
        resp = fetch_url(BING_SEARCH_URL.format(q=quote_plus(topic)))
        html = resp.content.decode(resp.encoding or "utf-8", errors="ignore")
        ex = _BingResultExtractor()
        ex.feed(html)
        questions = [q for q in ex.questions if _QUESTION_RE.match(q)]
        return {
            "titles": ex.titles[:MAX_BING_TITLES],
            "questions": questions[:MAX_PAA_QUESTIONS],
        }
    except Exception as e:
        log.info("bing keyword research skipped: %s", e.__class__.__name__)
        return {"titles": [], "questions": []}


def research_keywords(topic: str) -> dict:
    """Best-effort keyword research for a bare topic string.

    Returns {"primary_keyword": str, "secondary_keywords": [str],
    "questions": [str], "sources": {...}} — "sources" keeps the raw
    per-source findings for transparency/debugging, never fed to the LLM
    directly (only the derived primary/secondary/questions are).
    """
    autocomplete = _fetch_autocomplete(topic)
    bing = _fetch_bing_serp(topic)

    primary_keyword = autocomplete[0] if autocomplete else topic
    secondary = [s for s in autocomplete[1:] if s != primary_keyword]
    # de-dup case-insensitively while preserving order, cap the combined list
    seen = {primary_keyword.lower()}
    for candidate in bing["titles"]:
        key = candidate.lower()
        if key not in seen and len(secondary) < MAX_SUGGESTIONS:
            seen.add(key)
            secondary.append(candidate)

    return {
        "primary_keyword": primary_keyword,
        "secondary_keywords": secondary[:MAX_SUGGESTIONS],
        "questions": bing["questions"],
        "sources": {
            "autocomplete": autocomplete,
            "bing_titles": bing["titles"],
            "bing_questions": bing["questions"],
        },
    }

"""Unit tests for app.core.keyword_research — mocks the outbound fetch so no
real network calls happen; verifies best-effort fallback behavior when a
source fails, and the derived primary/secondary keyword shape."""

import json
from unittest.mock import MagicMock, patch

from app.core.keyword_research import research_keywords


def _fake_response(content: bytes, encoding: str | None = None):
    resp = MagicMock()
    resp.content = content
    resp.encoding = encoding
    return resp


def _autocomplete_response(suggestions: list[str]):
    payload = json.dumps(["compounding", suggestions]).encode("utf-8")
    return _fake_response(payload)


def _bing_html(titles: list[str], questions: list[str]):
    parts = [f"<h2>{q}</h2>" for q in questions] + [f"<h2>{t}</h2>" for t in titles]
    return _fake_response(("<html><body>" + "".join(parts) + "</body></html>").encode())


def test_research_keywords_uses_first_autocomplete_suggestion_as_primary():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = [
            _autocomplete_response(["compounding interest", "compounding daily"]),
            _bing_html([], []),
        ]
        result = research_keywords("compounding")

    assert result["primary_keyword"] == "compounding interest"
    assert "compounding daily" in result["secondary_keywords"]


def test_research_keywords_merges_bing_titles_into_secondary():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = [
            _autocomplete_response(["compounding interest"]),
            _bing_html(["What is compound interest guide"], []),
        ]
        result = research_keywords("compounding")

    assert "What is compound interest guide" in result["secondary_keywords"]


def test_research_keywords_extracts_paa_style_questions():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = [
            _autocomplete_response([]),
            _bing_html([], ["How does compounding work?", "not a question"]),
        ]
        result = research_keywords("compounding")

    assert "How does compounding work?" in result["questions"]
    assert "not a question" not in result["questions"]


def test_research_keywords_falls_back_to_topic_when_autocomplete_empty():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = [_autocomplete_response([]), _bing_html([], [])]
        result = research_keywords("compounding")

    assert result["primary_keyword"] == "compounding"
    assert result["secondary_keywords"] == []


def test_research_keywords_survives_autocomplete_failure():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = [Exception("network down"), _bing_html(["a title"], [])]
        result = research_keywords("compounding")

    assert result["primary_keyword"] == "compounding"  # falls back to topic
    assert "a title" in result["secondary_keywords"]


def test_research_keywords_survives_bing_failure():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = [
            _autocomplete_response(["compounding interest"]),
            Exception("network down"),
        ]
        result = research_keywords("compounding")

    assert result["primary_keyword"] == "compounding interest"
    assert result["questions"] == []


def test_research_keywords_survives_total_failure():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = Exception("network down")
        result = research_keywords("compounding")

    assert result["primary_keyword"] == "compounding"
    assert result["secondary_keywords"] == []
    assert result["questions"] == []


def test_research_keywords_survives_malformed_autocomplete_json():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = [_fake_response(b"not json"), _bing_html([], [])]
        result = research_keywords("compounding")

    assert result["primary_keyword"] == "compounding"


def test_research_keywords_dedupes_secondary_case_insensitively():
    with patch("app.core.keyword_research.fetch_url") as mock_fetch:
        mock_fetch.side_effect = [
            _autocomplete_response(["Compounding Interest"]),
            _bing_html(["compounding interest"], []),
        ]
        result = research_keywords("compounding")

    assert result["secondary_keywords"].count("compounding interest") <= 1

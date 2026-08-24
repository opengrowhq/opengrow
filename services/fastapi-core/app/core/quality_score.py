"""On-page quality scoring for a generated article draft.

No I/O: pure functions over the draft text + the brief/outline already held
in orchestrator state, so every branch is unit-testable without a database or
a model call (mirrors app.core.article_prompt's pure-composition contract).

v1 scope, deliberately: keyword/heading coverage, length-vs-target, and a
readability heuristic — all computable from data the pipeline already has.
Real "TF-IDF vs top-10 SERP" comparison (the BUILD-PLAN target metric) needs
a paid search API and is out of scope until one is provisioned; this scores
"did the draft do what the brief asked" rather than "does it out-rank
page-1 competitors."
"""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _normalize(text: str) -> str:
    return " ".join(_words(text))


def keyword_coverage_score(draft: str, brief: dict) -> float:
    """1.0 if the primary keyword appears in a heading or the first 200
    chars, plus coverage ratio of secondary keywords anywhere in the body."""
    primary = (brief.get("primary_keyword") or "").strip()
    secondary = [k for k in (brief.get("secondary_keywords") or []) if k.strip()]
    if not primary and not secondary:
        return 1.0  # nothing to check against — don't penalize a bare brief

    body_norm = _normalize(draft)
    headings = " ".join(_HEADING_RE.findall(draft))
    intro = draft[:200]

    scores = []
    if primary:
        hit = _normalize(primary) in _normalize(headings + " " + intro) or (
            _normalize(primary) in body_norm
        )
        scores.append(1.0 if hit else 0.0)
    if secondary:
        hits = sum(1 for kw in secondary if _normalize(kw) in body_norm)
        scores.append(hits / len(secondary))
    return sum(scores) / len(scores)


def heading_coverage_score(draft: str, sections: list[dict]) -> float:
    """Fraction of the approved outline's headings that appear (loosely) in
    the draft, plus a small credit for hitting a reasonable heading count
    when there's no outline to compare against."""
    draft_headings_norm = [_normalize(h) for h in _HEADING_RE.findall(draft)]
    if not sections:
        return 1.0 if draft_headings_norm else 0.0

    expected = [_normalize(s.get("heading", "")) for s in sections if s.get("heading")]
    if not expected:
        return 1.0 if draft_headings_norm else 0.0

    hits = sum(
        1
        for exp in expected
        if any(exp in got or got in exp for got in draft_headings_norm if got)
    )
    return hits / len(expected)


def length_score(draft: str, target_words: int) -> float:
    """1.0 within +/-20% of the target, tapering linearly to 0 by +/-60%."""
    actual = len(_words(draft))
    if target_words <= 0:
        return 1.0
    ratio = actual / target_words
    deviation = abs(1.0 - ratio)
    if deviation <= 0.2:
        return 1.0
    if deviation >= 0.6:
        return 0.0
    return 1.0 - (deviation - 0.2) / 0.4


def readability_score(draft: str) -> float:
    """Heuristic: average words/sentence. 12-22 words scores 1.0, tapering
    to 0 outside 5-40 — a crude stand-in for a real readability index that
    still catches wall-of-text paragraphs and overly choppy output."""
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(draft) if s.strip()]
    words = _words(draft)
    if not sentences or not words:
        return 0.0
    avg = len(words) / len(sentences)
    if 12 <= avg <= 22:
        return 1.0
    if avg < 12:
        return max(0.0, (avg - 5) / 7)
    return max(0.0, 1.0 - (avg - 22) / 18)


_WEIGHTS = {
    "keyword_coverage": 0.35,
    "heading_coverage": 0.25,
    "length": 0.2,
    "readability": 0.2,
}


def score_draft(draft: str, brief: dict, sections: list[dict] | None = None) -> dict:
    """Returns {"score": float 0-1, "breakdown": {dimension: float}}."""
    breakdown = {
        "keyword_coverage": keyword_coverage_score(draft, brief),
        "heading_coverage": heading_coverage_score(draft, sections or []),
        "length": length_score(draft, int(brief.get("length_words") or 1200)),
        "readability": readability_score(draft),
    }
    total = sum(breakdown[k] * w for k, w in _WEIGHTS.items())
    return {"score": round(total, 4), "breakdown": breakdown}


def feedback_for_retry(breakdown: dict) -> str:
    """Turn the weakest dimensions into a short instruction the draft prompt
    can be re-run with, so a retry actually addresses the shortfall instead
    of just re-rolling the same prompt."""
    notes = []
    if breakdown.get("keyword_coverage", 1.0) < 0.6:
        notes.append(
            "Weave the primary keyword into a heading and the opening paragraph, "
            "and use the secondary keywords naturally throughout."
        )
    if breakdown.get("heading_coverage", 1.0) < 0.6:
        notes.append("Cover every section from the approved outline, in order.")
    if breakdown.get("length", 1.0) < 0.6:
        notes.append("Match the target word count more closely — expand thin sections.")
    if breakdown.get("readability", 1.0) < 0.6:
        notes.append(
            "Vary sentence length — avoid long run-on sentences and avoid "
            "choppy one-line sentences."
        )
    return " ".join(notes)

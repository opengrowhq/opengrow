from app.core.quality_score import (
    feedback_for_retry,
    heading_coverage_score,
    keyword_coverage_score,
    length_score,
    readability_score,
    score_draft,
)

GOOD_DRAFT = (
    "## Why compounding matters\n"
    "Compounding is one of the most powerful forces in personal finance, and "
    "understanding compounding early changes how you plan for the long run. "
    "This guide walks through why compounding matters and how to use it.\n\n"
    "## How to get started\n"
    "Small, consistent contributions compound over time into large outcomes. "
    "The earlier you start, the more time compounding has to work in your favor, "
    "and even modest amounts add up meaningfully across a couple of decades."
)
BRIEF = {
    "primary_keyword": "compounding",
    "secondary_keywords": ["personal finance"],
    "length_words": 90,
}
SECTIONS = [
    {"heading": "Why compounding matters", "points": []},
    {"heading": "How to get started", "points": []},
]


def test_keyword_coverage_full_when_both_present():
    assert keyword_coverage_score(GOOD_DRAFT, BRIEF) == 1.0


def test_keyword_coverage_no_brief_keywords_does_not_penalize():
    assert keyword_coverage_score(GOOD_DRAFT, {}) == 1.0


def test_keyword_coverage_penalizes_missing_primary():
    score = keyword_coverage_score("nothing relevant here", BRIEF)
    assert score < 1.0


def test_heading_coverage_matches_outline():
    assert heading_coverage_score(GOOD_DRAFT, SECTIONS) == 1.0


def test_heading_coverage_zero_without_matching_headings():
    assert heading_coverage_score("no headings, just prose", SECTIONS) == 0.0


def test_heading_coverage_no_outline_credits_any_heading():
    assert heading_coverage_score("## Something\ntext", []) == 1.0
    assert heading_coverage_score("no headings at all", []) == 0.0


def test_length_score_perfect_at_target():
    text = "word " * 90
    assert length_score(text, 90) == 1.0


def test_length_score_tapers_for_short_draft():
    text = "word " * 20
    score = length_score(text, 90)
    assert 0.0 <= score < 1.0


def test_length_score_zero_far_below_target():
    assert length_score("one word", 1000) == 0.0


def test_length_score_no_target_never_penalizes():
    assert length_score("anything", 0) == 1.0


def test_readability_score_reasonable_sentences():
    assert readability_score(GOOD_DRAFT) > 0.5


def test_readability_score_empty_draft_is_zero():
    assert readability_score("") == 0.0


def test_readability_score_choppy_sentences_penalized():
    choppy = "Hi. Ok. Go. Now. Fast. Yes. No. Ok."
    assert readability_score(choppy) < 0.5


def test_score_draft_combines_dimensions():
    result = score_draft(GOOD_DRAFT, BRIEF, SECTIONS)
    assert 0.0 <= result["score"] <= 1.0
    assert set(result["breakdown"]) == {
        "keyword_coverage",
        "heading_coverage",
        "length",
        "readability",
    }


def test_score_draft_low_quality_scores_low():
    result = score_draft("bad", {"primary_keyword": "x", "length_words": 1000}, [])
    assert result["score"] < 0.4


def test_feedback_for_retry_flags_weak_dimensions():
    feedback = feedback_for_retry(
        {"keyword_coverage": 0.0, "heading_coverage": 1.0, "length": 1.0, "readability": 1.0}
    )
    assert "keyword" in feedback.lower()


def test_feedback_for_retry_empty_when_all_strong():
    feedback = feedback_for_retry(
        {"keyword_coverage": 1.0, "heading_coverage": 1.0, "length": 1.0, "readability": 1.0}
    )
    assert feedback == ""

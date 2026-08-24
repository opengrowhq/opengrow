from app.core.article_prompt import (
    OUTLINE_MAX_TOKENS,
    brand_system_block,
    compose_draft_prompt,
    compose_outline_prompt,
    draft_max_tokens,
)
from app.schemas.article import ArticleBrief
from app.schemas.generation import GenerationCreate


def test_article_brief_defaults_and_cleaning():
    b = ArticleBrief(
        topic="  Why founders blog  ", secondary_keywords=["seo", " seo ", ""]
    )
    assert b.topic == "Why founders blog"
    assert b.secondary_keywords == ["seo"]  # trimmed, de-duped, blanks dropped
    assert b.goal == "educate"
    assert b.length_words == 1200
    assert b.sections_target == 5


def test_article_brief_rejects_empty_topic():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ArticleBrief(topic="   ")


def test_generation_create_accepts_metadata():
    g = GenerationCreate(brief="x", metadata={"kind": "article_outline"})
    assert g.metadata == {"kind": "article_outline"}


BRIEF = {
    "topic": "Why founders should blog",
    "primary_keyword": "founder blogging",
    "secondary_keywords": ["content marketing"],
    "audience": "solo SaaS founders",
    "goal": "educate",
    "tone": "direct, practical",
    "length_words": 1500,
    "sections_target": 4,
    "notes": "mention distribution",
}
BRAND = {
    "tone": "warm but blunt",
    "audience": "indie hackers",
    "tagline": "Grow in the open",
}
OUTLINE = [{"heading": "Why blogging compounds", "points": ["SEO", "trust"]}]


def test_brand_block_includes_profile_fields():
    block = brand_system_block(BRAND)
    assert "warm but blunt" in block
    assert "indie hackers" in block


def test_brand_block_empty_without_profile():
    assert brand_system_block(None) == ""


def test_brand_block_is_length_capped():
    huge = {"tone": "x" * 5000, "audience": "y" * 5000}
    assert len(brand_system_block(huge)) <= 1200


def test_outline_prompt_carries_brief_and_brand():
    msgs = compose_outline_prompt(BRIEF, BRAND)
    assert msgs[0]["role"] == "system"
    joined = " ".join(m["content"] for m in msgs)
    assert "Why founders should blog" in joined
    assert "solo SaaS founders" in joined
    assert "warm but blunt" in joined  # brand conditioning reached the prompt
    assert "4" in joined  # sections_target


def test_outline_prompt_without_brand_still_works():
    joined = " ".join(m["content"] for m in compose_outline_prompt(BRIEF, None))
    assert "Why founders should blog" in joined


def test_draft_prompt_includes_outline_headings():
    joined = " ".join(m["content"] for m in compose_draft_prompt(BRIEF, OUTLINE, BRAND))
    assert "Why blogging compounds" in joined
    assert "1500" in joined


def test_context_is_injected_within_budget():
    context = [{"filename": "a.md", "snippet": "s" * 10_000}]
    joined = " ".join(
        m["content"] for m in compose_draft_prompt(BRIEF, OUTLINE, None, context)
    )
    assert "a.md" in joined
    assert joined.count("s") <= 6000  # char_budget respected


def test_outline_prompt_uses_system_template_override_when_given():
    msgs = compose_outline_prompt(BRIEF, None, None, "CUSTOM PLAYBOOK RULES")
    assert msgs[0]["content"].startswith("CUSTOM PLAYBOOK RULES")


def test_draft_prompt_uses_system_template_override_when_given():
    msgs = compose_draft_prompt(BRIEF, OUTLINE, None, None, "CUSTOM DRAFT RULES")
    assert msgs[0]["content"].startswith("CUSTOM DRAFT RULES")


def test_outline_prompt_falls_back_to_default_without_override():
    msgs = compose_outline_prompt(BRIEF)
    assert "senior content strategist" in msgs[0]["content"]


def test_token_budgets():
    assert OUTLINE_MAX_TOKENS < 2000
    assert draft_max_tokens(1500) > 2000  # long-form needs more than the old default
    assert draft_max_tokens(5000) <= 16000  # but stays bounded

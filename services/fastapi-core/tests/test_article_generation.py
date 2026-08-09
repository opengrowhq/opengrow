from types import SimpleNamespace

from app.core.generation_messages import build_generation_messages


class _Gen(SimpleNamespace):
    pass


def _gen(**meta):
    return _Gen(brief="fallback brief", reference_asset_id=None, metadata_json=meta)


def test_plain_generation_keeps_legacy_shape():
    messages, max_tokens = build_generation_messages(None, _gen())
    assert messages[0]["role"] == "system"
    assert "fallback brief" in messages[1]["content"]
    assert max_tokens == 2000


def test_outline_kind_uses_outline_prompt():
    gen = _gen(
        kind="article_outline",
        article={"topic": "Blogging for founders", "sections_target": 3},
    )
    messages, max_tokens = build_generation_messages(None, gen)
    joined = " ".join(m["content"] for m in messages)
    assert "Blogging for founders" in joined
    assert "Markdown list" in messages[0]["content"]
    assert max_tokens < 2000


def test_draft_kind_uses_draft_prompt_and_bigger_budget():
    gen = _gen(
        kind="article_draft",
        article={"topic": "Blogging", "length_words": 1500},
        outline=[{"heading": "Why it compounds", "points": ["SEO"]}],
    )
    messages, max_tokens = build_generation_messages(None, gen)
    joined = " ".join(m["content"] for m in messages)
    assert "Why it compounds" in joined
    assert max_tokens > 2000


def test_draft_kind_tolerates_uncoercible_length_words():
    from app.core.article_prompt import draft_max_tokens

    gen = _gen(
        kind="article_draft",
        article={"topic": "Blogging", "length_words": "long"},
    )
    messages, max_tokens = build_generation_messages(None, gen)
    assert max_tokens == draft_max_tokens(1200)


def test_brand_and_context_come_from_arguments():
    gen = _gen(
        kind="article_outline",
        article={"topic": "Blogging"},
    )
    messages, _ = build_generation_messages(
        None,
        gen,
        brand={"tone": "plain-spoken"},
        context=[{"filename": "story.md", "snippet": "we grew 3x in a year"}],
    )
    joined = " ".join(m["content"] for m in messages)
    assert "plain-spoken" in joined
    assert "we grew 3x in a year" in joined


def test_internal_metadata_keys_are_ignored():
    # _brand/_context used to be smuggled through metadata_json; they must no
    # longer influence the prompt (nor be required there).
    gen = _gen(
        kind="article_outline",
        article={"topic": "Blogging"},
        _brand={"tone": "SHOUTY"},
        _context=[{"filename": "x.md", "snippet": "secret internal chunk"}],
    )
    messages, _ = build_generation_messages(None, gen)
    joined = " ".join(m["content"] for m in messages)
    assert "SHOUTY" not in joined
    assert "secret internal chunk" not in joined

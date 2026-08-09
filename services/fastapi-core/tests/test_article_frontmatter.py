from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.content_piece import ContentStatus
from app.routers.content import _render_markdown, article_content_metadata


def test_article_fields_are_copied():
    out = article_content_metadata(
        {"next_action": "review"},
        {
            "slug": "why-blog",
            "description": "A case for blogging",
            "tags": ["seo", "seo"],
            "topic": "x",
        },
    )
    assert out["next_action"] == "review"
    assert out["article"] == {
        "slug": "why-blog",
        "description": "A case for blogging",
        "tags": ["seo"],
    }


def test_no_article_returns_base_unchanged():
    assert article_content_metadata({"next_action": "x"}, None) == {"next_action": "x"}
    assert article_content_metadata(None, None) is None


def test_blank_article_fields_are_omitted():
    out = article_content_metadata(None, {"slug": "  ", "tags": []})
    assert out is None


def _cp(**kw):
    base = dict(
        id="11111111-1111-1111-1111-111111111111",
        title="Why founders blog",
        body="## Intro\n\nText.\n",
        format="blog_post",
        status=ContentStatus.APPROVED,
        created_at=datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc),
        metadata_json={
            "article": {
                "slug": "why-founders-blog",
                "description": "The case for blogging",
                "tags": ["seo", "content"],
            }
        },
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_blog_post_frontmatter_is_blog_ready():
    md = _render_markdown(_cp())
    assert 'title: "Why founders blog"' in md
    assert "slug: why-founders-blog" in md
    assert "date: 2026-07-26" in md
    assert 'description: "The case for blogging"' in md
    assert 'tags: ["seo", "content"]' in md
    assert "draft: false" in md
    # internal fields must NOT leak into a public blog
    assert "11111111-1111-1111-1111-111111111111" not in md
    assert "status:" not in md
    assert "format:" not in md
    assert md.endswith("## Intro\n\nText.\n")


def test_blog_post_slug_falls_back_to_title():
    md = _render_markdown(_cp(metadata_json=None))
    assert "slug: why-founders-blog" in md


def test_draft_true_when_not_approved():
    md = _render_markdown(_cp(status=ContentStatus.DRAFT))
    assert "draft: true" in md


def test_quotes_in_title_are_escaped():
    md = _render_markdown(_cp(title='He said "hi": really'))
    assert 'title: "He said \\"hi\\": really"' in md


def test_non_article_format_keeps_minimal_frontmatter():
    md = _render_markdown(_cp(format="ad", metadata_json=None))
    assert 'title: "Why founders blog"' in md
    assert "date: 2026-07-26" in md
    assert "slug:" not in md
    assert "status:" not in md


def test_explicit_slug_is_sanitized():
    import yaml

    md = _render_markdown(
        _cp(
            metadata_json={
                "article": {"slug": "Foo Bar: Baz!", "description": "", "tags": []}
            }
        )
    )
    assert "slug: foo-bar-baz" in md
    frontmatter = md.split("---", 2)[1]
    parsed = yaml.safe_load(frontmatter)
    assert parsed["slug"] == "foo-bar-baz"

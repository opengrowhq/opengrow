---
name: meta-tags-for-blog-posts
description: Use when finalizing the slug, meta description, or tags for a blog post before it moves to APPROVED/PUBLISHED.
---

# Meta Tags for Blog Posts

## Overview

`slug`, `description`, and `tags` become the actual `<title>`, meta description, and URL shown in search results and social previews. Get these wrong and the click-through rate suffers regardless of how good the article is.

**Grounding note**: `slug`, `description`, and `tags` originate on `ArticleBrief` (`app/schemas/article.py`) and get carried onto the `ContentPiece` row via `app/core/article_metadata.py`, which writes them into `ContentPiece.metadata_json["article"]` (nested under an `"article"` key, not top-level). `app/routers/content.py`'s `_render_markdown()` reads them back from that exact path when exporting Markdown/publishing — `article.get("slug")`, `article.get("description")`, `article.get("tags")`. So the values this skill produces should be written to `metadata_json["article"].{slug,description,tags}`, not top-level `ContentPiece` columns (there are none) and not left as caller-only output.

## When to Use

- Finalizing a draft before `APPROVED`/`PUBLISHED`
- User asks for "SEO title," "meta description," or "slug" for a post
- Reviewing a draft that has a generic or missing title tag / description

## When NOT to Use

- Draft is still in outline stage (title is a working title, not final)
- Content format isn't published as a standalone page (e.g., social post, email)

## Core Pattern

1. **Title tag**: 50-60 characters, primary keyword near the front, no keyword stuffing, human-readable.
2. **Meta description**: 150-160 characters, includes the primary keyword naturally, states the concrete benefit/answer, ends with an implicit or explicit reason to click. Not a summary of the intro paragraph.
3. **Slug**: lowercase, hyphenated, short, keyword-relevant, no stop-word bloat, stable (avoid dates/numbers that go stale).
4. **Tags**: 3-6 tags, existing taxonomy terms preferred over inventing near-duplicates (e.g., don't add both `seo` and `search-engine-optimization`).

## Rules

- Title and meta description must not be truncated mid-word at typical SERP pixel widths — stay under the character budget, don't just count and hope.
- Do not repeat the exact H1 verbatim as the meta description.
- Avoid clickbait framing that the body doesn't deliver on.
- If the primary keyword doesn't fit naturally in the description, don't force it — natural language beats keyword density here.

## Output Format

```markdown
- Title tag (N chars): ...
- Meta description (N chars): ...
- Slug: ...
- Tags: [tag1, tag2, tag3]
```

## Common Mistakes

- Meta description that's just the first sentence of the article, cut off.
- Slug with stopwords and dates: `/2026/07/a-guide-to-the-best-tools-for-you`.
- Title tag over 60 characters that gets truncated with "..." in search results.
- Tags that duplicate existing taxonomy under a slightly different name.

---

*Adapted from BlogPilot's meta-title-rules.md and meta-description-rules.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

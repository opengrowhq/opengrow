---
name: social-repurposing
description: Use when turning a published or draft ContentPiece into an X/Twitter post or LinkedIn post, respecting each channel's real constraints.
---

# Social Repurposing

## Overview

X and LinkedIn are not "paste the article body" channels. The adapters (`app/core/publishers/x.py`, `linkedin.py`) post exactly what they're given, including truncation — bad repurposing ships broken posts, not just suboptimal ones.

## When to Use

- Repurposing a blog post / article into an X post or LinkedIn post
- User asks to "turn this into a tweet" or "make a LinkedIn post from this"

## When NOT to Use

- Long-form channels (WordPress/Ghost/Webflow) — see `cms-export-mapping`
- Content that has no independent value as a short-form post (too dependent on the full article's context)

## Channel Constraints (as actually implemented)

- **X** (`x.py`): body is hard-truncated to **280 characters** by the adapter itself (`body.strip()[:280]`) — no thread support, no auto-splitting. If you don't write a tight take under 280 chars, the adapter will cut it mid-sentence.
- **LinkedIn** (`linkedin.py`): posted as a plain text share (`shareMediaCategory: "NONE"`) via `shareCommentary.text` — no rich formatting, no image attachment in the current implementation. Longer-form is fine (no hard cap in the adapter), but LinkedIn's own UI truncates long posts behind "see more" around ~140-210 characters of visible preview.

## Core Pattern

1. **Write for the channel, don't excerpt the article** — a repurposed post should be a standalone take (a hook, a stat, a contrarian angle, a question), not "Read more about X" plus a link fragment.
2. **X**: write and count to ≤280 characters yourself before handing to the adapter — do not rely on the adapter's truncation to "handle it," since mid-sentence cuts look broken.
3. **LinkedIn**: front-load the hook in the first 1-2 lines (before the "see more" fold), since the adapter won't format anything for you.
4. **No formatting assumptions**: neither adapter supports Markdown/HTML rendering — plain text only.
5. **Attribute back to the source** — link to the full `ContentPiece` (once published) rather than duplicating the whole argument.

## Checklist

- [ ] X post is ≤280 characters as written, not relying on adapter truncation
- [ ] LinkedIn post's hook lands before the visible-preview fold
- [ ] No Markdown/HTML syntax left in the text (adapters post plain text)
- [ ] Post stands alone as a useful piece of content, not a teaser fragment
- [ ] Links back to the full piece where relevant

## Common Mistakes

- Pasting the article's intro paragraph as-is into the X post and letting it get truncated mid-word.
- Writing a LinkedIn post where the actual point only appears after the "see more" fold.
- Including Markdown syntax (`**bold**`, `[link](url)`) that renders as literal characters on both channels.

---

*Adapted from BlogPilot's social-repurposing.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

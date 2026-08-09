---
name: content-refresh
description: Use when updating an existing PUBLISHED ContentPiece whose traffic or accuracy has decayed, rather than writing something new.
---

# Content Refresh

## Overview

Updating an existing published post is usually higher-leverage than writing a new one: it already has backlinks, indexing history, and some ranking signal. Refreshing is a distinct task from drafting — the goal is targeted improvement, not a rewrite from scratch.

## When to Use

- A `PUBLISHED` `ContentPiece` has decaying traffic, outdated facts, or outdated screenshots/examples
- User asks to "update," "refresh," or "revive" an existing post
- Competitor content has surpassed the post in depth or currency

## When NOT to Use

- Post is fundamentally wrong in premise or targets a dead topic — write a new piece or archive instead of patching
- Post is recent and performing well — don't refresh just for the sake of it

## Core Pattern

1. **Diagnose before editing**: identify *why* it's stale — outdated facts/dates, new competitor content covering it better, broken links, missing a subtopic that's now commonly searched, or thin sections that need depth.
2. **Preserve what's working**: keep the URL/slug stable (never break existing backlinks/indexing), keep sections that still perform, keep the historical publish date visible if the platform shows one (add an "updated" date instead).
3. **Update surgically**: fix outdated facts, add missing subtopics, expand thin sections, refresh examples/screenshots/stats — don't rewrite sections that are already accurate and complete.
4. **Re-run relevant checks** after edits: `readability-targets`, `helpful-content-compliance`, and `meta-tags-for-blog-posts` if the title/description changed meaning.
5. **Log what changed and why** so the update is auditable (ties to `ContentPiece.metadata_json` history if the caller tracks revisions).

## Checklist

- [ ] Root cause of staleness identified (not just "it's old")
- [ ] Slug/URL unchanged
- [ ] Only stale/thin sections rewritten; accurate sections left alone
- [ ] Dates, stats, screenshots, and product references are current
- [ ] Newly common subtopics/questions added if missing
- [ ] Re-checked against `helpful-content-compliance` after edits

## Output

```markdown
- Staleness cause: ...
- Sections updated: [...]
- Sections left unchanged: [...]
- Facts/stats refreshed: [...]
```

## Common Mistakes

- Rewriting the entire post from scratch, losing accumulated ranking signal for no reason.
- Changing the slug, breaking existing inbound links.
- Bumping the "updated" date without making a substantive change (stale-content padding, which Google's helpful content system penalizes).
- Refreshing facts but not re-checking readability/compliance on the new sections.

---

*Adapted from BlogPilot's content-refresh-rules.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

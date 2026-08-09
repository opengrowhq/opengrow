---
name: internal-linking-for-opengrow
description: Use when drafting or reviewing a ContentPiece that should link to other content owned by the same tenant.
---

# Internal Linking for OpenGrow

## Overview

Internal links keep readers on the tenant's site and pass topical authority between posts. Every link must stay inside the same tenant's `ContentPiece` set — cross-tenant linking is both wrong and a tenant-isolation risk.

## When to Use

- Drafting a new `ContentPiece` with `format: blog_post` (or similar long-form format)
- Reviewing a draft before it moves to `IN_REVIEW`/`APPROVED` and it has no or too few internal links
- User asks to "add internal links" or "link to our other posts"

## When NOT to Use

- Tenant has no other `PUBLISHED` content pieces yet — do not force a link that doesn't exist
- Short-form content (social posts, ads) where internal links aren't idiomatic

## Known Gap

There is currently no dedicated API/service in the codebase for tenant-scoped content lookup or internal-link-graph building — only the `ContentPiece` model and its `status`/`title`/`body` fields. Until that exists:

- Do not claim to have "looked up" real posts unless the caller actually supplied a list of the tenant's other `PUBLISHED` `ContentPiece` titles/slugs.
- If no such list is supplied, use `[INTERNAL LINK: topic]` placeholders (see `outline-first-writing`) instead of fabricating URLs.

## Core Pattern

1. **Get the candidate link targets**: only `ContentPiece` rows for the same tenant with `status: PUBLISHED`. Never link across tenants.
2. **Match by topical relevance**, not just keyword overlap — a link should help the reader go deeper on a subtopic actually mentioned nearby.
3. **Place links naturally** inside body text near the relevant mention, not bunched in a "Related posts" dump unless that section is explicitly requested.
4. **Cap density**: roughly 1 internal link per 150-300 words of body content; more reads as spammy.
5. **Use descriptive anchor text** (the topic, not "click here" or the raw title if it's clunky mid-sentence).
6. **If no real target exists**, leave a `[INTERNAL LINK: topic]` placeholder rather than inventing a URL or slug.

## Output Format (when reviewing)

```markdown
- Internal links found: N
- Density: N per M words (target 1 per 150-300)
- Placeholder links needing real targets: [...]
- Cross-tenant or fabricated links found: none / [list — must fix]
```

## Common Mistakes

- Inventing a plausible-sounding URL or slug for a post that doesn't exist.
- Linking to content from a different tenant (hard isolation violation — treat as a bug, not a style issue).
- Stuffing every paragraph with a link ("keyword salad" density).
- Using generic anchor text like "read more here."

---

*Adapted from BlogPilot's internal-linking-graph.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

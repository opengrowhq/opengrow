---
name: content-cannibalization
description: Use when two or more of a tenant's own ContentPiece rows appear to target the same query, competing with each other in search.
---

# Content Cannibalization

## Grounding status

**Methodology-only for detection.** No tenant-scoped query/ranking-overlap detection tooling exists in OpenGrow yet (see the same gap noted in `internal-linking-for-opengrow`). This skill applies once the caller has identified two or more real `ContentPiece` rows that overlap — it does not describe an automated detection feature.

## Overview

When multiple pages from the same site target the same query, they split ranking signal and confuse search engines about which page to rank — both can underperform versus a single strong page.

## When to Use

- Two or more real `ContentPiece` titles/URLs are identified as covering near-identical ground
- Reviewing a new draft against existing published content for overlap before publish

## When NOT to Use

- Pages cover the same broad topic but target genuinely different intents/queries (e.g., "what is X" vs "X pricing") — that's healthy topical coverage, not cannibalization
- No second overlapping piece actually exists

## Core Pattern

1. **Confirm true overlap**: same primary query/intent, not just the same broad subject.
2. **Choose a resolution strategy**:
   - **Merge (301 redirect)**: if one page is clearly weaker/older, consolidate into the stronger one and redirect.
   - **Differentiate**: if both serve genuinely different angles, sharpen each page's title/intro/scope so they stop competing (e.g., split "beginner guide" vs "advanced guide").
   - **Canonicalize**: if near-duplicate for a legitimate reason (e.g., syndicated content), set a canonical tag pointing to the primary version.
3. **Never leave both pages targeting the identical query with no differentiation** — that's the actual problem, and doing nothing keeps splitting signal.

## Output

```markdown
- Pages in conflict: [A, B]
- True overlap confirmed: yes/no
- Recommended resolution: merge / differentiate / canonicalize
- Rationale: ...
```

## Common Mistakes

- Merging two pages that actually serve different search intents, losing coverage.
- Diagnosing cannibalization from topic similarity alone without checking actual target query overlap.
- Redirecting without preserving the stronger page's URL/backlink equity.

---

*Adapted from BlogPilot's content-cannibalization-resolution.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

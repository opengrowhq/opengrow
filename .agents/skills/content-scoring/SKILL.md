---
name: content-scoring
description: Use when comparing a draft's topical coverage against top-ranking competitor content for the same query.
---

# Content Scoring

## Grounding status

**Methodology-only.** No competitor-content fetching, TF-IDF, or SERP-comparison tooling exists in OpenGrow yet. Requires the caller to supply real competitor content/SERP data — this skill does not describe a built feature.

## Overview

Content scoring compares a draft's term/topic coverage against what's actually ranking for the target query, to catch coverage gaps a purely internal quality review would miss.

## When to Use

- Real competitor URLs or their content is supplied for comparison
- Draft is targeting a competitive query and needs a coverage gap-check before publish

## When NOT to Use

- No competitor content is actually available to compare against
- Topic has no meaningful competitive SERP (branded/internal queries)

## Core Pattern

1. Identify the target query and the actual top-ranking pages for it (supplied by the caller, not assumed).
2. Extract the subtopics/entities/terms those pages cover that the draft doesn't.
3. Distinguish real gaps (a subtopic readers expect, genuinely missing) from noise (incidental terms with no topical value).
4. Recommend specific additions, not a vague "add more depth."

## Output

```markdown
- Query: ...
- Competitor coverage gaps found: [...]
- Recommended additions: [...]
- Coverage verdict: comprehensive / gaps found
```

## Common Mistakes

- Scoring against competitors without real data — inventing plausible-sounding gaps.
- Chasing every term a competitor uses regardless of relevance (keyword stuffing risk).
- Treating word count as a proxy for coverage quality.

---

*Adapted from BlogPilot's content-score-rules.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

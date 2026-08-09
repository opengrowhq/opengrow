---
name: helpful-content-compliance
description: Use when reviewing a blog post draft before publication, especially when the draft feels generic, thin, summary-heavy, or search-engine-first.
---

# Helpful Content Compliance

## Overview

Google's Helpful Content System demotes content that is primarily made for search engines rather than people. Run this checklist before every publish.

## When to Use

- Final review before publishing a blog post
- Traffic to an existing post is decaying
- Draft feels generic, regurgitated, or keyword-stuffed
- Post summarizes competitors without adding original value

## When NOT to Use

- Output is not meant for search (internal docs, support replies)
- Draft is intentionally a curated list or link roundup labeled as such

## The Checklist

For each item, answer **YES**, **NO**, or **N/A**. A post with any **NO** on a high-severity item should not publish without revision.

### Content quality (high severity)

- [ ] Provides original information, reporting, research, or analysis
- [ ] Provides substantial, complete, or comprehensive description
- [ ] Adds insightful analysis beyond the obvious
- [ ] Adds substantial value if based on other sources (not just rewriting)
- [ ] Headline avoids exaggeration or shock
- [ ] Is worth bookmarking, sharing, or recommending
- [ ] Would fit in a printed magazine, encyclopedia, or book

### Expertise (high severity)

- [ ] Trustworthy presentation with clear sourcing or evidence of expertise
- [ ] Site/author appears well-trusted in the topic
- [ ] Written by someone who demonstrably knows the topic
- [ ] Free of easily-verified factual errors
- [ ] Trustworthy enough for money-or-life (YMYL) decisions if applicable

### Presentation (medium severity)

- [ ] Free of spelling or stylistic issues
- [ ] Does not appear sloppy or hastily produced
- [ ] Not mass-produced or outsourced to the point of losing care
- [ ] Not overloaded with distracting ads

### Made-for-search red flags (high severity)

- [ ] Primarily made for humans, not search engines
- [ ] Not topic-sprawling to catch random traffic
- [ ] Not extensively automated or low-effort
- [ ] Not mainly summarizing others without added value
- [ ] Not chasing trends without real audience interest
- [ ] Does not leave readers needing to search again
- [ ] Not written to a word-count myth
- [ ] Not entering a niche without real expertise
- [ ] Does not promise an answer that does not exist

## Output

Return a short structured report:

```markdown
- Overall: PASS / REVIEW / FAIL
- Score: X/22
- High-severity failures:
  - ...
- Required fixes:
  - ...
```

Threshold: ≥20/22 = pass; 17-19 = review; ≤16 = fail (do not publish).

## Common Mistakes

- Giving a vague "needs work" verdict without citing specific checklist items.
- Approving content that is clearly a rewrite of top-10 SERP results.
- Ignoring red flags because the prose is grammatically clean.

---

*Adapted from BlogPilot's google-helpful-content.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

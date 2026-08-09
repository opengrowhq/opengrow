---
name: llms-txt-generation
description: Use when generating an llms.txt or llms-full.txt file to help AI crawlers/assistants understand a site's content.
---

# llms.txt Generation

## Grounding status

**Methodology-only.** No `llms.txt` generation exists in OpenGrow yet — no route, no build step producing it. This skill is a reference for the emerging `llms.txt` convention, not a built feature.

## Overview

`llms.txt` (and the fuller `llms-full.txt`) is an emerging, still-informal convention: a Markdown file at the site root that gives AI systems a curated, structured summary of a site's key content — analogous to `robots.txt` but for LLM consumption rather than crawl directives.

## When to Use

- Building or reviewing an `llms.txt`/`llms-full.txt` file for a tenant's site
- User asks about AI-crawler-readable site summaries

## When NOT to Use

- The feature doesn't exist in the product yet — don't claim OpenGrow auto-generates this today

## Core Pattern (per the emerging spec)

1. **`llms.txt`**: short, curated — H1 site name, one-line description, then a Markdown list of key pages with brief descriptions, grouped under H2 sections (e.g., "Docs", "Guides").
2. **`llms-full.txt`** (optional): the fuller version — same structure but with more complete content inlined, for systems that want fuller context without following links.
3. **Keep it curated, not exhaustive** — this isn't a sitemap dump; prioritize the pages that best represent the site's value.
4. **Plain Markdown, no HTML** — the format intentionally stays simple for LLM parsing.

## Output Format

```markdown
# Site Name

> One-line description of what this site/product is.

## Docs
- [Page title](url): one-line description

## Guides
- [Page title](url): one-line description
```

## Common Mistakes

- Dumping every URL on the site instead of curating the most valuable ones.
- Including marketing fluff instead of concise factual descriptions.
- Treating this as implemented in OpenGrow today when it isn't.

---

*Adapted from BlogPilot's llms-txt-spec.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

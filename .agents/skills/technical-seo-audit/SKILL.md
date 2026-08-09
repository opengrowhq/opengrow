---
name: technical-seo-audit
description: Use when running a technical SEO health check on a site or page — crawlability, indexability, and structural issues, not content quality.
---

# Technical SEO Audit

## Grounding status

**Methodology-only.** No audit crawler, site-scanning, or technical-SEO-check code exists in OpenGrow yet. This skill is a manual checklist to apply when a human (or an external tool's output) provides the relevant data — it does not describe a built OpenGrow feature. Revisit once an audit module exists to ground this properly.

## Overview

Technical SEO issues (crawl errors, indexability blocks, broken structure) can suppress even excellent content. This is a distinct pass from content-quality review (`helpful-content-compliance`) — it's about whether the page can be found and read correctly at all.

## When to Use

- User provides crawl data, Search Console output, or asks to audit a site/page technically
- Diagnosing why a page isn't appearing in search despite good content

## When NOT to Use

- No crawl/technical data is available — don't fabricate audit findings from the article text alone
- Reviewing content quality/E-E-A-T — use `helpful-content-compliance` or `eeat-compliance` instead

## Core Checklist Categories

- **Crawlability**: robots.txt not blocking important paths, no accidental `noindex`, XML sitemap present and accurate, no orphan pages
- **Indexability**: canonical tags correct (no conflicting signals), no duplicate-content cannibalization, redirect chains resolved (not multi-hop)
- **URL structure**: clean, descriptive, stable slugs; no unnecessary parameters indexed
- **Mobile/rendering**: content is server-rendered or otherwise crawlable (not client-JS-only for critical content)
- **Status codes**: no broken internal links (404s), no soft-404s, redirects use correct codes (301 vs 302)
- **Structured data validity**: any schema markup present validates without errors (see `schema-article` etc.)
- **Page speed signals**: see `core-web-vitals` for LCP/INP/CLS specifics

## Output

```markdown
- Audit scope: [site / single page]
- Critical issues: [...]
- Warnings: [...]
- Passed checks: [...]
```

## Common Mistakes

- Treating a slow page as a "content problem" when it's a technical rendering issue.
- Flagging issues without underlying crawl/tool data to support the claim.
- Confusing a 301 redirect chain with a single clean redirect.

---

*Adapted from BlogPilot's technical-seo-audit.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

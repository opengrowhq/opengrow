---
name: schema-article
description: Use when generating Article/BlogPosting JSON-LD structured data for a ContentPiece.
---

# Schema: Article

## Grounding status

**Methodology-only.** No JSON-LD generation exists anywhere in the OpenGrow codebase yet (confirmed: no `application/ld+json` references in `services/fastapi-core` or `services/frontend`). This skill documents the correct schema shape for when that feature is built — it does not describe current OpenGrow behavior.

## Overview

`Article`/`BlogPosting` JSON-LD tells search engines structured facts about a piece of content (headline, author, dates, image) beyond what they can infer from HTML alone, enabling rich results.

## When to Use

- Designing or implementing Article schema generation for `ContentPiece`
- Validating existing Article JSON-LD on a published page

## When NOT to Use

- Content type isn't an article (see `schema-faq`, `schema-howto`, `schema-product` for those)

## Required/Recommended Fields

```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "...",
  "datePublished": "ISO 8601",
  "dateModified": "ISO 8601",
  "author": { "@type": "Person", "name": "..." },
  "publisher": { "@type": "Organization", "name": "...", "logo": { "@type": "ImageObject", "url": "..." } },
  "image": "...",
  "mainEntityOfPage": { "@type": "WebPage", "@id": "canonical URL" }
}
```

- `headline`: keep under ~110 characters (Google truncates longer).
- `datePublished`/`dateModified`: real ISO 8601 timestamps, not placeholder/build-time dates.
- `author`: must match the actual visible byline, not a generic placeholder.
- `image`: must be a real, accessible URL meeting minimum dimensions for rich results.

## Common Mistakes

- `dateModified` that never changes even after real content edits (or worse, auto-bumped on every deploy with no real edit — both mislead ranking systems).
- Author name in schema not matching the visible page byline.
- Missing `mainEntityOfPage`, which can cause ambiguity on pages with multiple schema blocks.

---

*Adapted from BlogPilot's schema-article.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

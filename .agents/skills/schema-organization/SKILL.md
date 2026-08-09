---
name: schema-organization
description: Use when generating Organization or Person JSON-LD structured data for brand/author identity.
---

# Schema: Organization / Person

## Grounding status

**Methodology-only.** No JSON-LD generation exists in OpenGrow yet. Once built, this would likely draw on the real `Brand` model (`app/models/brand.py`) for organization identity fields (`name`, tagline from `profile`) rather than inventing new ones.

## Overview

`Organization` and `Person` schema establish canonical identity for a brand or author across the web, supporting knowledge panels and author/publisher attribution in rich results.

## When to Use

- Establishing site-wide Organization schema for a tenant's brand
- Adding Person schema for an article's author (see `schema-article`'s `author` field, and `eeat-author-bios`-style trust signals from `eeat-compliance`)

## When NOT to Use

- No real, stable brand/author identity exists yet to describe

## Required Shape (Organization)

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "...",
  "url": "...",
  "logo": "...",
  "sameAs": ["social profile URLs..."]
}
```

## Required Shape (Person)

```json
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": "...",
  "url": "author page URL if it exists",
  "sameAs": ["social/professional profile URLs..."]
}
```

## Rules

- `sameAs` links must be real, owned profiles — not arbitrary third-party mentions.
- Organization `name`/`logo` should match the tenant's actual `Brand` identity once that data is wired in, not a placeholder.
- Person schema should only be used for real, identifiable authors — not a generic "Staff Writer" if a specific person actually wrote it.

## Common Mistakes

- Inventing `sameAs` links that don't belong to the actual entity.
- Using a single generic Organization schema for what should be distinct Person (author) attribution.

---

*Adapted from BlogPilot's schema-organization.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

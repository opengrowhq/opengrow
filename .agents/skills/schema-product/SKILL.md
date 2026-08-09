---
name: schema-product
description: Use when generating Product JSON-LD structured data for a page describing a purchasable product or a pricing tier.
---

# Schema: Product

## Grounding status

**Methodology-only.** No JSON-LD generation exists in OpenGrow yet. This skill documents the correct schema shape for when that feature is built.

## Overview

`Product` JSON-LD marks up price, availability, and review data for rich results (price snippets, star ratings) in search.

## When to Use

- A page describes a specific purchasable product, plan, or pricing tier with a real price
- Validating existing Product schema against the visible page content

## When NOT to Use

- Page is informational/comparison content that mentions products without being a product/pricing page itself
- No real price or availability data exists to mark up

## Required Shape

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "...",
  "description": "...",
  "offers": {
    "@type": "Offer",
    "price": "...",
    "priceCurrency": "...",
    "availability": "https://schema.org/InStock"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "...",
    "reviewCount": "..."
  }
}
```

## Rules

- `price`/`availability` must match what's actually shown and true on the page — mismatched price schema is a common cause of manual actions.
- `aggregateRating` must reflect real review data, never a fabricated or estimated rating/count.
- Don't apply Product schema to a general feature/blog page just because it mentions the product.

## Common Mistakes

- Stale `price` in schema after a real pricing change on the visible page.
- Fabricated `aggregateRating` with no underlying reviews (explicit rich-results guideline violation).
- Marking up a comparison/roundup article as if each mentioned product were the page's own Product.

---

*Adapted from BlogPilot's schema-product.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

---
name: schema-faq
description: Use when generating FAQPage JSON-LD structured data for a ContentPiece's FAQ section.
---

# Schema: FAQ

## Grounding status

**Methodology-only.** No JSON-LD generation exists in OpenGrow yet. Pair with `faq-section-writing` for the content itself; this skill covers the structured-data markup once that feature is built.

## Overview

`FAQPage` JSON-LD marks up question/answer pairs so search engines can render them as expandable rich results directly in search listings.

## When to Use

- The page has a real, visible FAQ section (see `faq-section-writing`) and needs matching schema
- Validating existing FAQ schema against the visible page content

## When NOT to Use

- No visible FAQ section exists on the page — schema must match visible content; don't add FAQPage schema for content the user can't actually see (a guideline violation, not just poor practice)

## Required Shape

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "The exact visible question text",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The exact visible answer text"
      }
    }
  ]
}
```

## Rules

- Schema text must match the visible page text exactly — no schema-only content invented to game the rich result.
- Only mark up genuine, visible FAQ content, not every question mentioned anywhere on the page.
- Keep `acceptedAnswer.text` plain and complete — it's what shows in the rich result.

## Common Mistakes

- Schema Q&A pairs that don't exist visibly on the page (policy violation, risks manual action).
- Marking up marketing copy dressed as fake questions to get more rich-result real estate.
- Answer text in schema diverging from the visible answer after a content edit.

---

*Adapted from BlogPilot's schema-faq.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

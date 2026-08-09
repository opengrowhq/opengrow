---
name: schema-howto
description: Use when generating HowTo JSON-LD structured data for a step-by-step ContentPiece.
---

# Schema: HowTo

## Grounding status

**Methodology-only.** No JSON-LD generation exists in OpenGrow yet. This skill documents the correct schema shape for when that feature is built.

## Overview

`HowTo` JSON-LD marks up sequential step-by-step instructions so search engines can render numbered steps directly in results.

## When to Use

- The page contains a genuine, ordered, step-by-step procedure
- Validating existing HowTo schema against the visible steps

## When NOT to Use

- Content is a listicle or general guide without true sequential steps — don't force HowTo schema onto non-procedural content
- Steps aren't genuinely ordered/dependent (if order doesn't matter, it isn't a HowTo)

## Required Shape

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to ...",
  "step": [
    {
      "@type": "HowToStep",
      "name": "Step name",
      "text": "Step instructions",
      "image": "optional image URL"
    }
  ],
  "totalTime": "optional ISO 8601 duration"
}
```

## Rules

- Steps in schema must match the visible, numbered steps on the page — same visible-content-parity rule as FAQ schema.
- Use `HowToStep.name` for a short step label and `.text` for the full instruction — don't collapse both into one field.
- Only include `totalTime`/`estimatedCost` if the claim is genuinely accurate, not a guess.

## Common Mistakes

- Applying HowTo schema to a general "tips" article that has no real step order.
- Schema steps not matching visible page steps after an edit.
- Inventing a `totalTime` estimate with no basis.

---

*Adapted from BlogPilot's schema-howto.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

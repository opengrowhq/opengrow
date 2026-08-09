---
name: hreflang-implementation
description: Use when a tenant publishes the same content in multiple languages/regions and needs correct hreflang signaling.
---

# Hreflang Implementation

## Grounding status

**Methodology-only.** OpenGrow has no multi-language/locale publishing feature yet (no locale field on `ContentPiece`, no hreflang generation). This skill applies once such a feature exists — it's a reference for correct implementation, not a description of built OpenGrow behavior.

## Overview

`hreflang` tells search engines which language/region variant of a page to serve to which searchers. Implemented wrong, it causes the wrong language version to rank, or search engines to ignore the signal entirely.

## When to Use

- A future multi-language publishing feature is being designed or reviewed
- Auditing hreflang tags on already-published multi-locale content

## When NOT to Use

- Single-language site (not applicable)

## Core Rules

- Every language/region variant must list **all** variants, including itself (self-referencing).
- Use `x-default` for the fallback/language-selector page, if one exists.
- Hreflang must be **reciprocal**: if page A links to page B via hreflang, B must link back to A, or the signal is ignored.
- Use correct ISO codes: language (`en`, `fr`) or language-region (`en-US`, `en-GB`) — don't mix region-only codes without a language.
- Each URL in the hreflang set must be the canonical URL for that variant, not a redirect target.

## Checklist

- [ ] All variants (including self) listed on every page in the set
- [ ] Reciprocal links confirmed both directions
- [ ] `x-default` present if a language-selector/fallback exists
- [ ] Correct ISO language/region codes
- [ ] URLs point to canonical versions, not redirects

## Common Mistakes

- Non-reciprocal hreflang (A links to B, B doesn't link back) — search engines ignore the whole set.
- Using hreflang to solve a duplicate-content problem instead of true localization.
- Forgetting the self-referencing entry.

---

*Adapted from BlogPilot's hreflang-implementation.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

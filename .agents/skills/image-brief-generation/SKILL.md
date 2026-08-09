---
name: image-brief-generation
description: Use when specifying what images a draft needs — placement, alt text, and whether an existing Asset can be reused via retrieval instead of generating something new.
---

# Image Brief Generation

## Overview

OpenGrow has a real `Asset` model (`app/models/asset.py`) for tenant-owned images: uploaded, virus-scanned (`AssetStatus`: UPLOADED → SCANNING → SCANNED → EMBEDDING → INDEXED), with an `embedding` + `text_snippet` for retrieval (Postgres ranking in lite mode, mirrored to Qdrant in production). An image brief should default to **retrieving an existing tenant asset** before assuming a new image must be created.

## When to Use

- Finalizing a draft's image placements (pairs with the "Suggested images" section in `outline-first-writing`'s output)
- Reviewing a draft with vague or missing image direction

## When NOT to Use

- Draft has no natural image placements (short-form text-only content)

## Core Pattern

1. **Check for a reusable asset first**: does the tenant already have an `INDEXED` `Asset` whose `text_snippet`/embedding matches this placement's need? Prefer reuse over a fresh brief when a good match exists.
2. **If no match, write a brief, not just a placeholder**: specify subject, style/mood, composition, and any brand-palette constraint (tie to `Brand.profile` if available — see `brand-voice-conditioning`).
3. **Placement**: name the exact section (intro / after H2 "X" / conclusion), not just "somewhere in the article."
4. **Alt text**: descriptive, specific to the image's content and its role in that section — not the filename, not keyword-stuffed, not "image of X."
5. **Only reference `SCANNED`/`INDEXED` assets** as available for use — `UPLOADED`/`SCANNING`/`SCAN_FAILED`/`EMBED_FAILED` assets aren't safely retrievable yet.

## Checklist

- [ ] Checked for a reusable indexed asset before briefing a new image
- [ ] Placement names the specific section, not "somewhere"
- [ ] Alt text is descriptive and specific, not generic or keyword-stuffed
- [ ] Brief references brand palette/style constraints if a Brand profile exists
- [ ] No reference to an asset that isn't in `SCANNED`/`INDEXED` status

## Output Format

```markdown
### Image brief: [section name]
- Reuse candidate: Asset [id] (if a strong match exists) / none found
- Subject: ...
- Style/mood: ...
- Alt text: ...
```

## Common Mistakes

- Briefing a brand-new image when a matching indexed asset already exists.
- Generic alt text ("image1.jpg" or "picture of product") with no descriptive value.
- Vague placement ("add an image somewhere here") that doesn't survive into actual publishing.

---

*Adapted from BlogPilot's image-brief-generation.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

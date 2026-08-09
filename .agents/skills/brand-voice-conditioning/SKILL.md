---
name: brand-voice-conditioning
description: Use when drafting or reviewing any customer-facing content for a tenant that has a Brand profile, to make the output actually sound like that brand instead of generic AI voice.
---

# Brand Voice Conditioning

## Overview

A `Brand` row stores extracted "Brand DNA" in `profile` (JSONB): tone, palette, tagline, audience, pains, do/don't phrases. Voice consistency only happens if this data is pulled into the prompt every time — it does not happen automatically just because the row exists.

## When to Use

- Generating or editing a `ContentPiece` for a tenant that has a `READY` Brand
- Reviewing a draft for voice/tone drift before it moves to `IN_REVIEW` or `APPROVED`
- User says content "doesn't sound like us" or "sounds too generic/AI"

## When NOT to Use

- Tenant has no Brand row, or `Brand.status` is not `READY` (PENDING/SCRAPING/EXTRACTING/FAILED) — fall back to a neutral, professional default voice and say so
- Purely technical/internal content with no brand-facing audience

## Core Pattern

1. **Load `Brand.profile`** for the tenant before drafting. If missing or not `READY`, state that explicitly rather than inventing a voice.
2. **Extract the conditioning fields**: tone descriptors, tagline, audience description, pain points, and any explicit do/don't phrase lists.
3. **Inject as constraints, not decoration** — the tone/audience/pains must shape section framing and examples, not just appear as a stray adjective in the intro.
4. **Enforce do/don't phrases literally** — treat "don't" phrases as hard bans, not soft suggestions.
5. **Self-check before returning**: read the draft back against the tone descriptors. If it reads like generic AI copy that could belong to any brand, revise.

## Voice Drift Checklist

- [ ] Tone descriptors from `profile.tone` are reflected in sentence rhythm and word choice, not just claimed
- [ ] Audience from `profile.audience` matches the assumed reader knowledge level
- [ ] At least one pain point from `profile.pains` is addressed concretely, not abstractly
- [ ] No banned phrase from `profile` do/don't list appears anywhere in the draft
- [ ] Tagline or its underlying promise is not contradicted by the piece
- [ ] Draft would not read as interchangeable with a competitor's generic blog post

## Output

When reviewing (not drafting), return:

```markdown
- Brand voice match: PASS / DRIFT / FAIL
- Tone: matches / drifts — evidence
- Banned phrases found: none / [list]
- Fixes required: ...
```

## Common Mistakes

- Mentioning the tagline once and calling it "on-brand."
- Treating `profile.pains` as copy to insert verbatim instead of a lens for framing.
- Applying a brand voice to a tenant whose Brand is still `SCRAPING`/`EXTRACTING` — the profile isn't finalized yet.
- Ignoring do/don't phrases because they seem minor.

---

*Adapted from BlogPilot's brand-voice-extraction.md and post-writer-style-matching.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

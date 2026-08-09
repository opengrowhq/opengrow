---
name: readability-targets
description: Use when reviewing a draft's prose quality — sentence length, paragraph length, passive voice, and reading grade level.
---

# Readability Targets

## Overview

Readable prose keeps readers on the page and helps content get cited/skimmed correctly by both humans and AI summarizers. This is a mechanical pass, separate from factual or structural review.

## When to Use

- Final pass on a draft before `APPROVED`
- Draft reads dense, academic, or hard to skim
- User asks to "simplify" or "make more readable"

## When NOT to Use

- Deeply technical reference content where precision requires longer sentences (still trim where possible, but don't force artificial simplicity that loses accuracy)

## Targets

- **Reading level**: aim for roughly Flesch-Kincaid grade 7-9 for general blog content (adjust up for technical/developer audiences, but flag if it drifts past grade 12 unintentionally).
- **Sentence length**: average 15-20 words; flag sentences over 30 words for splitting.
- **Paragraph length**: 2-4 sentences for web content; one clear idea per paragraph.
- **Passive voice**: keep under ~10% of sentences; prefer active voice, especially in instructional content.
- **Transition words**: present in a healthy share of sentences (however, because, for example) to aid flow — but not mechanically forced into every sentence.

## Core Pattern

1. Scan for sentences over 30 words — split or simplify.
2. Scan for paragraphs over 5 sentences — break up.
3. Flag passive constructions where an active rewrite is more direct ("mistakes were made" → "we made mistakes").
4. Check that jargon is either avoided or defined on first use for the target audience.
5. Re-estimate grade level after edits; don't just eyeball it.

## Output

```markdown
- Est. reading grade: N
- Avg sentence length: N words
- Sentences over 30 words: N
- Passive voice: N% of sentences
- Fixes applied / recommended: ...
```

## Common Mistakes

- Simplifying to the point of losing necessary technical precision.
- Treating passive voice as always wrong — sometimes it's the natural phrasing ("the request was rejected by the server" is fine when the actor is genuinely unimportant).
- Fixing sentence length but ignoring paragraph density.

---

*Adapted from BlogPilot's readability-targets.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

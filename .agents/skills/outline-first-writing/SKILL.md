---
name: outline-first-writing
description: Use when generating a long-form blog post, article, or guide from a brief or topic, before producing the full draft.
---

# Outline-First Writing

## Overview

Produce the structure before the prose. A validated outline prevents expensive rewrites and keeps long-form content aligned with the brief, audience, and search intent.

## When to Use

- User asks for a blog post, article, guide, or long-form piece
- The brief includes target length, audience, tone, or number of sections
- Multiple angles or section orders are possible

## When NOT to Use

- User asks only for an outline
- User asks for a rewrite of an existing draft
- Output is a short social post, ad, email, or single-paragraph copy

## Core Pattern

1. **Ask clarifying questions** if the brief is vague (audience, goal, length, must-cover points).
2. **Produce a structured outline** with H2 sections and 2-4 H3 bullets each.
3. **Present the outline** to the user and ask for approval or edits.
4. **Only after approval**, write the full draft following the approved outline exactly.

## Output Format

```markdown
## Working Title

**Goal:** one-line intent (educate | compare | convert)
**Audience:** ...
**Target length:** ... words

### TL;DR
- Key takeaway 1
- Key takeaway 2
- Key takeaway 3

### Outline
1. ## Section heading
   - Point to cover
   - Point to cover
   - [INTERNAL LINK: related topic]
2. ## Next section heading
   - ...

### Suggested images
- Placement: intro | section-2 | ... — Alt text: ...

### Open questions
- ...
```

## Rules

- Open with a TL;DR block (3-5 bullets). It trains the draft to answer the core question up front.
- Each H2 must match search intent:
  - Informational → definition → details → examples → edge cases
  - Commercial → what it is → best for whom → pros/cons → alternatives
  - Transactional → why → how to choose → step-by-step → next steps
- One section should target a featured snippet: H2 as a direct question, first paragraph 40-55 words answering it.
- Include `[INTERNAL LINK: topic]` placeholders where a related post exists or should exist.
- Add image suggestions with alt-text placeholders.
- Do not write the full draft until the user approves the outline.

## Common Mistakes

- Jumping straight to a 1,000+ word draft.
- Outline with only H2s and no bullets.
- Outline so rigid the user cannot reshape it.
- Draft that ignores the approved outline or invents new sections.

---

*Adapted from BlogPilot's outline-structure.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

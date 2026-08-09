---
name: passage-ranking-optimization
description: Use when drafting or reviewing long-form content so that individual H2/H3 sections can rank or be cited independently, not just the page as a whole.
---

# Passage Ranking Optimization

## Overview

Search engines and AI answer engines (AI Overviews, chat assistants) can surface a single passage — one H2/H3 section — independent of the full page ranking. Each section should stand alone as a citable, self-contained answer.

## When to Use

- Drafting any long-form `ContentPiece` with multiple H2/H3 sections
- Reviewing a draft where sections depend heavily on earlier context to make sense
- Optimizing an existing post for AI Overviews / snippet citation

## When NOT to Use

- Short-form content with a single continuous narrative (no discrete sections)
- Sections that are intentionally sequential steps in a procedure (still keep each step self-contained where possible, but strict standalone framing is less critical)

## Core Pattern

1. **One clear topic per section** — a section should answer one question or cover one subtopic, not blend two.
2. **Self-contained opening sentence** — the first sentence of a section should make sense without having read the sections before it (restate the subject, don't rely on "it" or "this" referring back).
3. **Front-load the answer** — state the core fact/answer in the first 1-2 sentences of the section, then elaborate.
4. **Use the heading as a real question or clear topic label** — headings that are vague ("More considerations") don't help passage extraction.
5. **Keep each passage a reasonable extractable length** — roughly 40-100 words for the core answer, with supporting detail after.

## Checklist

- [ ] Each H2/H3's first sentence doesn't depend on prior section context to parse
- [ ] Each section answers one clear question, statable as the heading itself
- [ ] Core answer appears in the first 1-2 sentences, not buried at the end
- [ ] No section requires reading the whole article to be useful in isolation

## Output (when reviewing)

```markdown
- Sections reviewed: N
- Non-self-contained sections: [heading — why]
- Fixes required: ...
```

## Common Mistakes

- Section opens with "As mentioned above..." or "This also means..." with no restated subject.
- Answer to the section's implicit question is in the last sentence instead of the first.
- Two subtopics crammed under one heading, making neither one a clean citable passage.

---

*Adapted from BlogPilot's passage-ranking-optimization.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

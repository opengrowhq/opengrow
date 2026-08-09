---
name: faq-section-writing
description: Use when adding an FAQ section to a blog post or article, sourced from real reader questions rather than invented ones.
---

# FAQ Section Writing

## Overview

A good FAQ section answers questions readers actually ask (People Also Ask / autocomplete-style patterns), each with a direct, complete, self-contained answer. A bad one pads word count with rephrased versions of the article's own headings.

## When to Use

- Post covers a topic with common follow-up or clarifying questions
- User asks for an "FAQ section" to be added to a draft
- Reviewing a draft whose existing FAQ section is thin or redundant with the body

## When NOT to Use

- Topic has no natural follow-up questions beyond what the body already covers
- Adding an FAQ would just restate the article's H2s as questions (low-value padding)

## Core Pattern

1. **Source real questions**: derive from what the intended reader would plausibly search next — genuine gaps, edge cases, or clarifications not fully covered in the body, not the same ground rephrased.
2. **3-6 questions is typical** — enough to be useful, not so many it becomes a second article.
3. **Each answer is self-contained**: 2-4 sentences, direct answer first (same discipline as `featured-snippet-targeting`).
4. **No duplicate ground** — if the body already fully answers something, don't re-ask it in the FAQ just to pad length.
5. **Phrase questions the way a person types them**, not as marketing copy.

## Checklist

- [ ] Every FAQ question is something a real reader would plausibly ask, not invented filler
- [ ] No FAQ question duplicates a body section's heading verbatim
- [ ] Each answer is self-contained and direct in its first sentence
- [ ] Question count is proportionate to the topic (not padded to hit a number)

## Output Format

```markdown
### FAQ

**Question as the reader would phrase it?**
Direct answer in 2-4 sentences.

**Next question?**
Direct answer.
```

## Common Mistakes

- FAQ section that's just the article's H2s with a question mark added.
- Answers that repeat "As discussed above..." instead of standing alone.
- Padding to 8+ questions when the topic only supports 3-4 genuine ones.

---

*Adapted from BlogPilot's faq-paa-targeting.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

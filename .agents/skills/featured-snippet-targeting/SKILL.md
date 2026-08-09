---
name: featured-snippet-targeting
description: Use when a section of a draft should target a Google featured snippet (position zero) for a question-style query.
---

# Featured Snippet Targeting

## Overview

Featured snippets pull a short, direct passage to answer a query at the top of search results. The pattern is mechanical: phrase the heading as the question, answer it directly and completely in 40-55 words immediately after.

## When to Use

- Outline or draft includes a section targeting a question-style search query ("what is...", "how does...", "why does...")
- Reviewing a draft that has the right topic but buries or hedges the direct answer

## When NOT to Use

- Section covers a broad topic with no single-sentence answer (comparison tables, long procedural walkthroughs are handled differently)
- Content isn't intended to rank in search (internal docs)

## Core Pattern

1. **Heading = the question**, phrased the way a user would search it ("What is X?" not "Understanding X").
2. **First paragraph after the heading = the direct answer**, 40-55 words, self-contained (see `passage-ranking-optimization`).
3. **No hedging or throat-clearing** before the answer — don't open with "Great question!" or three sentences of setup.
4. **Elaborate after**, not before, the direct answer — supporting detail, examples, and nuance go in subsequent paragraphs.
5. **Match the snippet type to the query**: definition question → paragraph snippet; "how to" → numbered list; comparison → table.

## Checklist

- [ ] Heading phrased as the actual search query
- [ ] Direct answer appears in the first paragraph, 40-55 words
- [ ] No filler sentence before the answer
- [ ] Snippet format (paragraph/list/table) matches the query type
- [ ] Answer is accurate and complete on its own, not a teaser for the rest of the section

## Output (when reviewing)

```markdown
- Snippet-target sections: N
- Word count of direct answer: N (target 40-55)
- Hedging/filler before answer: yes/no
- Fixes required: ...
```

## Common Mistakes

- Answer paragraph is 150+ words — too long to be pulled as a snippet.
- Heading phrased as a topic label instead of the actual question ("X Explained" instead of "What Is X?").
- Direct answer split across two paragraphs instead of one self-contained block.

---

*Adapted from BlogPilot's featured-snippet-targeting.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

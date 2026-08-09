---
name: topic-authority-scoring
description: Use when assessing whether content demonstrates entity-level topical authority (Wikipedia/Wikidata-style entity coverage) on a subject.
---

# Topic Authority Scoring

## Grounding status

**Methodology-only.** No entity-extraction, Wikipedia/Wikidata lookup, or authority-scoring tooling exists in OpenGrow yet. This is a manual assessment framework, not a built feature.

## Overview

Search engines increasingly reason about entities (people, places, concepts, organizations) and their relationships, not just keyword strings. Content that correctly names, relates, and contextualizes relevant entities signals topical depth beyond surface keyword matching.

## When to Use

- Assessing whether a piece demonstrates real subject-matter depth versus surface-level keyword coverage
- Topic has well-known entities (products, people, standards, organizations) that a knowledgeable piece should reference correctly

## When NOT to Use

- Topic has no meaningful entity graph (highly novel or purely opinion content)

## Core Pattern

1. Identify the core entities the topic should plausibly reference (named tools, standards, people, organizations, related concepts).
2. Check the draft: are the important entities present, named correctly, and related to each other accurately?
3. Check for entity errors: misattribution, outdated facts, wrong relationships (e.g., confusing two similarly-named tools).
4. Assess breadth vs depth: does the piece cover the entity's real neighborhood, or fixate on one narrow slice while ignoring adjacent, expected entities?

## Output

```markdown
- Core entities expected: [...]
- Entities present and correct: [...]
- Entities missing or misrepresented: [...]
- Authority verdict: strong / adequate / thin
```

## Common Mistakes

- Treating entity name-dropping as authority without correct relational context.
- Flagging entity gaps that aren't actually relevant to the piece's specific angle.

---

*Adapted from BlogPilot's topic-authority-scoring.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

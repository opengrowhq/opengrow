---
name: ai-overviews-capture
description: Use when writing or reviewing content intended to be cited in Google AI Overviews or similar AI-generated search answers.
---

# AI Overviews Capture

## Grounding status

**Methodology-only.** No AI Overview citation tracking exists in OpenGrow yet. This skill is a writing pattern to apply during drafting/review, not a measurement feature.

## Overview

AI Overviews and similar AI-generated answer boxes pull short, self-contained, well-attributed passages to cite. The same discipline as `passage-ranking-optimization` and `featured-snippet-targeting` applies, with extra weight on clear factual statements and source credibility.

## When to Use

- Drafting content on a question-style topic likely to trigger an AI Overview
- Reviewing why a page isn't getting cited in AI answers despite ranking well

## When NOT to Use

- Purely narrative/opinion content with no discrete factual claims to cite

## Core Pattern

1. **Direct, unambiguous factual statements** — AI systems favor passages with clear, extractable claims over hedged or vague phrasing.
2. **Self-contained passages** (see `passage-ranking-optimization`) — a citable passage shouldn't require surrounding context to be correct.
3. **Clear attribution/expertise signals** near the fact (see `eeat-compliance`) — AI systems weigh source credibility in what they choose to cite.
4. **Structured formatting helps extraction** — lists, defined terms, and clear headings are easier to parse and cite than dense prose.
5. **Accuracy is non-negotiable** — getting cited with a wrong fact is worse than not being cited.

## Checklist

- [ ] Key facts stated directly, not hedged into vagueness
- [ ] Passages are self-contained and accurate in isolation
- [ ] Source credibility signals present near factual claims
- [ ] Structure (lists/headings) supports easy extraction

## Common Mistakes

- Hedging every claim so heavily nothing is confidently citable.
- Burying a clear, citable fact inside a long unstructured paragraph.

---

*Adapted from BlogPilot's ai-overviews-capture.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

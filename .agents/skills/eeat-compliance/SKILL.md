---
name: eeat-compliance
description: Use when drafting or reviewing content on topics involving expertise, financial, medical, legal, or safety claims (YMYL), to make sure trust signals are present.
---

# E-E-A-T Compliance

## Overview

Experience, Expertise, Authoritativeness, Trustworthiness (E-E-A-T) is Google's framework for judging whether content and its source can be trusted, and it weighs heaviest on Your-Money-Your-Life (YMYL) topics: health, finance, legal, safety.

## When to Use

- Draft makes factual, financial, medical, legal, or safety claims
- Topic could influence a reader's money, health, or major life decisions
- Final review before `APPROVED`/`PUBLISHED` on any YMYL-adjacent post

## When NOT to Use

- Purely product-feature or how-to-use-OpenGrow content with no external factual claims
- Internal-only content never intended for a public reader

## Core Pattern

1. **Identify YMYL surface area**: does the draft make claims that, if wrong, could cost a reader money, harm their health, or expose them to legal risk?
2. **Check for first-hand experience signals**: does the piece show the author actually did the thing (screenshots, specific numbers, "when we tested X"), not just paraphrase what others say?
3. **Check for expertise attribution**: is there an author byline, or does OpenGrow's own product/data back the claim?
4. **Check sourcing**: are non-obvious factual claims attributed to a source, not asserted bare?
5. **Check for verifiable accuracy**: flag any claim that reads as unverifiable or suspiciously precise without a source.

## Checklist

- [ ] Experience: shows first-hand use/testing, not just secondhand summary
- [ ] Expertise: author or brand credibility is evident (byline, credentials, or demonstrated product knowledge)
- [ ] Authoritativeness: claims align with what a knowledgeable source in this space would say
- [ ] Trustworthiness: sources cited for non-obvious facts; no unverifiable stats stated as fact
- [ ] YMYL claims (financial/legal/health/safety) are qualified appropriately, not stated as absolute guarantees
- [ ] No factual claim that would embarrass the brand if fact-checked publicly

## Output

```markdown
- E-E-A-T: PASS / REVIEW / FAIL
- YMYL topic: yes / no
- Missing signals: ...
- Unsourced claims: ...
```

## Common Mistakes

- Treating E-E-A-T as only "add an author bio" — the content itself must demonstrate experience and accuracy.
- Stating financial/health outcomes as guaranteed ("this will double your revenue") instead of qualified.
- Citing a source that doesn't actually say what the draft claims it says.

---

*Adapted from BlogPilot's eeat-checklist.md and eeat-author-bios.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

---
name: content-decay-detection
description: Use when identifying which published content pieces are losing search traffic over time and need a content-refresh.
---

# Content Decay Detection

## Grounding status

**Methodology-only.** No traffic/Search-Console-integration exists in OpenGrow yet. This skill applies once the caller supplies real traffic/impressions data — it does not describe a built feature. Once identified, hand decayed pieces to `content-refresh`.

## Overview

Content decay is a gradual traffic/ranking decline on a previously-performing page. Catching it early (trailing-average trend, not single-week noise) makes refresh work far more effective than catching it after traffic has bottomed out.

## When to Use

- Real Search Console / analytics data (clicks, impressions, average position over time) is supplied
- Periodic review of published content health

## When NOT to Use

- No real traffic data exists to evaluate
- Page never had meaningful traffic to decay from (that's an initial-ranking problem, not decay)

## Core Pattern

1. **Use a trailing average** (e.g., 4-week trailing) rather than week-over-week, to filter out normal noise.
2. **Compare against the page's own historical peak**, not against other pages — decay is relative to itself.
3. **Distinguish decay causes**: seasonal (expected, don't refresh), competitive (someone else out-published you — refresh needed), staleness (facts/examples outdated — refresh needed), or algorithm-update-driven (may need bigger structural changes, not just a refresh).
4. **Flag for `content-refresh`** once trailing-average decline is confirmed and cause is identified — don't just flag "this is decaying," identify why.

## Output

```markdown
- Piece: ...
- Trailing-avg trend (4wk): declining X% / stable / growing
- Likely cause: seasonal / competitive / stale-facts / algo-update
- Refresh recommended: yes/no
```

## Common Mistakes

- Flagging normal seasonal dips as decay requiring action.
- Reacting to a single bad week instead of a sustained trailing-average trend.
- Recommending refresh without diagnosing the actual cause first.

---

*Adapted from BlogPilot's gsc-decay-detection.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

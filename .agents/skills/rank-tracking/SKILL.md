---
name: rank-tracking
description: Use when interpreting or planning rank-tracking data (search position over time) for a tenant's published content.
---

# Rank Tracking

## Grounding status

**Methodology-only.** No rank-tracking/SERP-scraping infrastructure exists in OpenGrow yet. This skill applies once the caller supplies real rank-tracking data from an external source — it does not describe a built feature.

## Overview

Rank tracking measures a page's search position for target queries over time. The value is in cadence and interpretation, not just having the raw numbers.

## When to Use

- Real rank-tracking data (position over time, from an external tool) is supplied
- Deciding how often to check ranks for a given content set

## When NOT to Use

- No real tracking data source exists — don't estimate or guess current rankings

## Core Pattern

1. **Cadence should match volatility**: highly competitive/volatile queries benefit from more frequent checks (e.g., weekly); stable long-tail queries need less (e.g., monthly).
2. **Trend over snapshot**: a single day's rank is noisy (SERP volatility, personalization, A/B tests on Google's side); look at multi-point trends before drawing conclusions.
3. **Segment by intent**: don't average rankings across informational and transactional queries as if they're comparable signals.
4. **Correlate with real changes**: a rank drop right after a content edit or a Google algorithm update is more actionable than an unexplained drift.

## Output

```markdown
- Query: ...
- Rank trend (last N checks): [...]
- Volatility: stable / volatile
- Likely cause if changed: [content edit / algo update / unclear]
```

## Common Mistakes

- Reacting to single-day rank fluctuations as if they were a firm trend.
- Checking ranks so infrequently that real decay goes unnoticed for months.
- Ignoring that scraping-based rank checks (vs official APIs) carry inherent noise/rate-limit risk.

---

*Adapted from BlogPilot's rank-tracking-cadence.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

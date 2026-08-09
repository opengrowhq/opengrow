---
name: core-web-vitals
description: Use when evaluating or discussing page-speed/UX performance metrics (LCP, INP, CLS) for a published page.
---

# Core Web Vitals

## Grounding status

**Methodology-only.** OpenGrow has no performance-monitoring or Core Web Vitals measurement integration yet. This skill applies when a human supplies real Lighthouse/CrUX/PageSpeed data — it does not describe a built OpenGrow feature.

## Overview

Core Web Vitals are Google's UX-quality signals: Largest Contentful Paint (LCP), Interaction to Next Paint (INP), Cumulative Layout Shift (CLS). They factor into ranking and directly affect conversion/bounce.

## When to Use

- Real Lighthouse/PageSpeed Insights/CrUX data is available to evaluate
- Diagnosing a specific reported performance complaint

## When NOT to Use

- No real measurement data is available — don't estimate or guess vitals from source code alone without a stated caveat
- The question is about content/SEO structure, not rendering performance

## Thresholds (Google's published "Good" bar)

- **LCP** (Largest Contentful Paint): ≤ 2.5s good, 2.5-4.0s needs improvement, > 4.0s poor
- **INP** (Interaction to Next Paint): ≤ 200ms good, 200-500ms needs improvement, > 500ms poor
- **CLS** (Cumulative Layout Shift): ≤ 0.1 good, 0.1-0.25 needs improvement, > 0.25 poor

## Core Pattern

1. Confirm the data source (lab data like Lighthouse vs field data like CrUX — they can disagree).
2. Compare each metric against the thresholds above.
3. For failures, identify the likely cause category: LCP → large hero image/slow server response; INP → heavy JS blocking main thread; CLS → images/ads without reserved dimensions, late-loading fonts.
4. Report field data (real users) as more authoritative than lab data (synthetic) when both are available.

## Output

```markdown
- LCP: Xs (Good/Needs Improvement/Poor)
- INP: Xms (Good/Needs Improvement/Poor)
- CLS: X (Good/Needs Improvement/Poor)
- Data source: lab / field
- Likely causes: ...
```

## Common Mistakes

- Reporting lab data as if it were real-user field data.
- Guessing vitals from reading source code instead of stating no measurement exists.
- Treating "needs improvement" as equivalent to "poor" — the ranking/UX impact differs.

---

*Adapted from BlogPilot's core-web-vitals-thresholds.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

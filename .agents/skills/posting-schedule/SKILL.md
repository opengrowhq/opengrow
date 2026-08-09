---
name: posting-schedule
description: Use when recommending the best day/time to publish or schedule a ContentPiece for a given channel.
---

# Posting Schedule

## Grounding status

**Methodology-only.** No send-time-optimization or channel-analytics infrastructure exists in OpenGrow yet (the real scheduling code in `calendar.mjs`/`content-calendar.tsx` handles due-date bucketing, not optimal-time recommendation — see `content-calendar-design`). This skill is generic best-practice guidance to apply until real per-tenant engagement data exists.

## Overview

Best publish time varies by channel and audience; generic "best time to post" advice is a weak starting default, not a substitute for a tenant's own engagement data once it exists.

## When to Use

- No tenant-specific engagement data exists yet, and a reasonable default time is needed
- Explaining why timing matters for a given channel

## When NOT to Use

- Real tenant analytics/engagement-by-time data is available — use that instead of generic defaults

## Generic Defaults (industry baseline, not OpenGrow-measured)

- **Blog/SEO content**: publish time matters less than for social — search traffic accrues over time regardless of hour. Prioritize consistency of cadence over specific hour.
- **X**: weekday mid-morning to early afternoon in the audience's primary timezone tends to see higher engagement; avoid very early morning/late night.
- **LinkedIn**: weekday mornings (especially Tue-Thu) typically outperform weekends for B2B audiences.
- **Email**: mid-morning weekday sends (Tue-Thu) are a common safe default; avoid Monday morning (inbox backlog) and Friday afternoon (lower open rates).

## Core Pattern

1. State clearly that these are generic defaults, not tenant-measured data, whenever no real data exists.
2. Once real engagement data exists for a tenant, prefer it over any generic default immediately.
3. For blog/SEO content, weight consistency of publishing cadence over exact timing.

## Common Mistakes

- Presenting generic "best time to post" defaults as if they were measured for this specific tenant.
- Over-indexing on exact hour for SEO content, where cadence and quality matter more.

---

*Adapted from BlogPilot's posting-schedule.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

---
name: content-calendar-design
description: Use when planning or organizing a tenant's upcoming ContentPiece schedule, or when reviewing why the content calendar view looks unbalanced.
---

# Content Calendar Design

## Overview

OpenGrow's calendar is a due-date scheduling view over existing `ContentPiece` rows (`due_at` field, bucketed by `calendarBucket()` in `services/frontend/src/features/content/calendar.mjs` into Overdue / Today / Tomorrow / Later, sorted by `sortByDueDate()`). This skill is about planning what goes into that schedule well, not just filling dates.

## When to Use

- User asks to plan out upcoming content ("what should we publish next few weeks")
- Reviewing an existing calendar that looks lopsided (all one topic, all one format, clustered dates)
- Assigning `due_at` to a batch of drafted `ContentPiece` rows

## When NOT to Use

- Scheduling a single one-off post with an obvious date
- Deep keyword/topic research to decide *what* to write about — that's a separate, currently-unbuilt capability (see Known Gap)

## Known Gap

BlogPilot's original methodology assumes pillar-and-spoke calendars driven by keyword research and topic-cluster data. OpenGrow has no keyword/SERP research backend yet — there is no `content-gap-analysis`, `topic-cluster-model`, or `paa-research` skill built, because there's no real data source to ground them on. Until that exists, calendar planning here is about **pacing and balance of already-decided topics**, not keyword-driven topic discovery.

## Core Pattern

1. **Check existing due dates first** — pull current `ContentPiece.due_at` values before adding more, so new dates don't cluster on top of existing ones. The real mechanism: `GET /content` (`list_content` in `app/routers/content.py`, returns `list[ContentPieceOut]`, each row has `due_at`) — fetch that list, then apply `calendarBucket()`/`sortByDueDate()` client-side to see the current spread before proposing new dates.
2. **Space by cadence, not convenience** — if the tenant publishes weekly, don't put 3 posts due the same day and then a two-week gap.
3. **Balance format and topic** — avoid scheduling five posts in a row on the same subtopic or all the same `format` (e.g., all `blog_post`, none social/email) unless that's intentional.
4. **Respect `Overdue`** — an item already past `due_at` should be resolved (republish date or drop) before adding new dates, not left to rot under new items.
5. **Leave buffer before real deadlines** — set `due_at` to the internal target, not the external commitment date, if review/edit time is needed.

## Checklist

- [ ] New `due_at` values don't collide with or crowd existing scheduled items
- [ ] No topic/format is overrepresented in a given week without reason
- [ ] No `Overdue` items being silently buried under new schedule entries
- [ ] Cadence matches what the tenant actually publishes at (don't over-schedule)

## Output Format

```markdown
### Proposed schedule
| Due date | Title | Format | Bucket |
|---|---|---|---|
| ... | ... | ... | Today/Tomorrow/Later |

### Balance check
- Topic spread: ...
- Format spread: ...
- Overdue items needing resolution: ...
```

## Common Mistakes

- Scheduling by convenience (next available date) instead of by actual publishing cadence.
- Ignoring existing `Overdue` items while adding a fresh batch of `due_at` dates.
- Assuming keyword-driven topic clustering is available when it isn't built yet — don't fabricate SERP/search-volume rationale for date choices.

---

*Adapted from BlogPilot's content-calendar-design.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

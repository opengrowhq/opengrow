---
name: serp-features-targeting
description: Use when deciding which SERP feature (featured snippet, FAQ rich result, HowTo, image pack, etc.) a piece of content should target.
---

# SERP Features Targeting

## Grounding status

**Methodology-only.** No SERP-feature tracking exists in OpenGrow yet. This is a planning framework to apply during outline/draft stage, tying together the other schema and snippet skills.

## Overview

Different SERP features suit different content shapes and query intents. Targeting the right one — and structuring content to actually qualify for it — is more effective than generic "SEO optimization."

## When to Use

- Planning a piece's structure during outline stage (pairs with `outline-first-writing`)
- Deciding which schema type(s) apply to a piece

## When NOT to Use

- Content genuinely doesn't fit any SERP feature shape (some content is just narrative)

## Feature → Content Shape Map

- **Featured snippet** (paragraph): direct question heading + 40-55 word answer → see `featured-snippet-targeting`
- **Featured snippet** (list/table): "best X", "steps to Y", comparison content → numbered/bulleted structure
- **FAQ rich result**: genuine Q&A section → see `faq-section-writing` + `schema-faq`
- **HowTo rich result**: true sequential procedure → see `schema-howto`
- **Image pack**: visually-driven topics (recipes, DIY, design) with well-alt-tagged original images
- **AI Overview citation**: authoritative, self-contained factual passages → see `ai-overviews-capture`

## Core Pattern

1. Identify the query's dominant intent and existing SERP feature (if visible) before drafting.
2. Pick one primary feature to target per section — don't try to hit every feature type in one paragraph.
3. Structure that section to genuinely qualify (see the specific linked skill), not just superficially resemble the format.
4. Add matching schema markup once that capability exists (see `schema-*` skills).

## Common Mistakes

- Targeting a feature the query doesn't actually surface (check real SERP behavior, don't guess).
- Structuring for a feature without the underlying content actually being complete/accurate enough to deserve it.

---

*Adapted from BlogPilot's serp-features-targeting.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

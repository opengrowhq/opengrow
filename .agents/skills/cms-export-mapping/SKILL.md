---
name: cms-export-mapping
description: Use when preparing a ContentPiece body for publishing to WordPress, Ghost, or Webflow, so formatting survives the channel's actual API shape.
---

# CMS Export Mapping

## Overview

WordPress, Ghost, and Webflow each expect content in a different shape. Publishing the same Markdown/HTML blindly to all three produces broken formatting on at least one. The adapters in `app/core/publishers/{wordpress,ghost,webflow}.py` are thin — they do not reformat content for you.

## When to Use

- A `ContentPiece` is about to be published via `WORDPRESS`, `GHOST`, or `WEBFLOW`
- Reviewing why published content looks broken on one channel but not another
- Adding a new CMS destination for a tenant

## When NOT to Use

- Publishing via `GITHUB_PR` — that has its own dedicated endpoint/flow, not the generic publisher registry
- Social/email channels (`X`, `LINKEDIN`, `EMAIL`) — see `social-repurposing` / `newsletter-excerpt` instead

## Channel Shapes (as actually implemented)

- **WordPress** (`wordpress.py`): `POST /wp-json/wp/v2/posts` with `{title, content, status}`. `content` accepts raw HTML — Markdown will render literally unless converted first. `status` defaults to `"publish"`; use `"draft"` for review-before-live flows.
- **Ghost** (`ghost.py`): `POST /ghost/api/admin/posts/?source=html` with `{posts: [{title, html, status}]}`. Body must be HTML (`source=html`), not raw Markdown or Ghost's Lexical/Mobiledoc format. `status` defaults to `"published"`.
- **Webflow** (`webflow.py`): `POST /collections/{collection_id}/items` with `fieldData: {name, slug, [body_field]: body}`. The body field name is **collection-specific** (default `"post-body"`) — must match the tenant's actual CMS collection schema, not assumed. Slug is auto-derived from title (lowercased, non-alphanumeric → hyphens, 256 char cap) — do not pass a separate slug.

## Core Pattern

1. **Convert body to HTML** before WordPress/Ghost publish if the source is Markdown — neither adapter converts it for you.
2. **Confirm the Webflow `body_field`** matches the tenant's actual collection schema; wrong field name silently writes to a field the theme doesn't render.
3. **Set `status` deliberately** — `"draft"` vs `"publish"`/`"published"` — don't default to live-publish for content still in review.
4. **Don't assume a returned URL** — Webflow's adapter currently returns an empty `url` (only `external_ref`); don't tell a user "here's the link" for a Webflow publish without checking.

## Checklist

- [ ] Body is HTML, not raw Markdown, for WordPress/Ghost
- [ ] Webflow `body_field` config matches the real collection field name
- [ ] `status` set intentionally (draft vs live)
- [ ] Not assuming a live URL exists for channels that don't return one (Webflow)

## Common Mistakes

- Sending Markdown straight to WordPress/Ghost and getting literal `**bold**` text on the live post.
- Using the default `body_field: "post-body"` for a Webflow collection that actually names it something else — content silently doesn't appear.
- Publishing with the adapter's default status (live) when the intent was a draft for review.

---

*Adapted from BlogPilot's cms-export-mapping.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

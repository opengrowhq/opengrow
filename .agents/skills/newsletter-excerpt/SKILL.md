---
name: newsletter-excerpt
description: Use when turning a ContentPiece into an email/newsletter send via the EMAIL publisher channel.
---

# Newsletter Excerpt

## Overview

The `EMAIL` publisher (`app/core/publishers/email.py`) sends plain-text email via SMTP (Mailpit locally, BYOK SMTP for real delivery). It has no HTML template engine, no image embedding, and no subject-line optimization — those decisions are entirely on the caller.

## When to Use

- Repurposing a `ContentPiece` into a newsletter/email send
- User asks to "email this to subscribers" or "turn this into a newsletter"

## When NOT to Use

- Transactional/system email (not a content-repurposing task)
- Channels with rich HTML templates already handled elsewhere in the product

## Channel Constraints (as actually implemented)

- `build_message()` sets `msg.set_content(body)` — **plain text only**, no HTML multipart in the current implementation. Markdown syntax will show as literal characters.
- `subject` defaults to the `title` if not explicitly set — a good article title is not always a good subject line (see below).
- `to` accepts a comma-separated string or list; no per-recipient personalization/merge fields exist.
- Sender defaults to `no-reply@opengrow.dev` unless overridden.

## Core Pattern

1. **Write a real subject line, don't just reuse the title** — subject lines that work as email opens (curiosity, benefit, urgency) differ from SEO-optimized article titles (keyword-forward, descriptive).
2. **Excerpt, don't dump the full article** — lead with the core value in the first 2-3 sentences (this is a plain-text email, there's no "click to expand"), then a clear link/CTA to the full piece if it lives elsewhere.
3. **Strip Markdown/HTML syntax** before sending — the adapter sends body text verbatim as plain text.
4. **Keep paragraphs short** — plain-text email with no rendering has no visual hierarchy beyond line breaks and blank lines.

## Checklist

- [ ] Subject line is written for the inbox, not copy-pasted from the article title
- [ ] Opening 2-3 sentences deliver real value on their own (plain-text, no preview truncation control)
- [ ] No Markdown/HTML syntax left in the body
- [ ] Recipients list (`to`) is correct before send — there is no preview/undo in this adapter

## Common Mistakes

- Reusing an SEO title verbatim as the email subject line — low open rates.
- Sending the full HTML-formatted article body as plain text, producing a wall of `#`/`**`/`[]()` syntax.
- Forgetting the adapter has no dry-run — a bad `to` list sends for real.

---

*Adapted from BlogPilot's newsletter-excerpt.md, MIT licensed. See https://github.com/IamRamgarhia/BlogPilot-Open-Source-AI-SEO-Content-Studio*

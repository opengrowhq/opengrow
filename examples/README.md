# Examples

Fixtures for trying OpenGrow's workflow end-to-end without writing your own
test data first.

- **`brand-voice-founder-saas.txt`** — sample brand-voice source text. Paste
  into brand extraction to see how OpenGrow derives tone, tagline, audience,
  pains, and do/don't phrases.
- **`content-briefs.json`** — three realistic `ArticleBrief` payloads
  (matches `app/schemas/article.py`) for driving article generation.
- **`sample-content-repo/`** — what a target repo for GitHub PR publishing
  looks like: plain Markdown under `content/posts/`, frontmatter shaped like
  OpenGrow's own Markdown export (`_render_markdown()` in
  `app/routers/content.py`).
- **`analytics-events.csv`** / **`revenue-events.csv`** — sample rows for
  `POST /analytics/import` (matches `AnalyticsImportRow` in
  `app/schemas/analytics.py`). `revenue_cents` is in cents, not dollars.

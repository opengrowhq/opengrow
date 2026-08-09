<div align="center">

# OpenGrow Roadmap

**What's shipped, what's next, and the business-impact order of work.**

[README](./README.md) · [AGENTS.md](./AGENTS.md) · [ASSUMPTIONS.md](./ASSUMPTIONS.md)

</div>

---

## Status: Pre-Alpha (v0.1.0)

Auth, asset upload, AI generation, the full content lifecycle, GitHub PR publishing, and revenue attribution are in place, with a tenant-scoped Next.js app at `/app/[slug]`. The API is now first-class: API keys for headless access, an MCP server for AI agents, usage metering, optional rate limiting, multi-channel publishing (WordPress/Ghost), and an orchestrator run endpoint. See `services/fastapi-core/docs/API.md`.

## Where we're headed

OpenGrow generates marketing content from your company context, publishes it through the channels founders already use, and ties each piece back to whether it created traffic, signups, pipeline, or revenue.

## The first wedge

We looked closely at the AI content/SEO tool landscape — closed SaaS products and open-source self-hosted alternatives alike. Two things are missing from the first workflow OpenGrow is attacking:

1. **GitHub PR-based publishing.** Every tool we found publishes via manual export or a CMS plugin at best. None open a pull request against your own blog repo the way a developer would expect.
2. **Revenue attribution.** No tool — open or closed source — connects a specific piece of content to the revenue it actually generated. Everyone stops at traffic and rankings.

These are not the entire product. They are the first wedge: a narrow, useful, differentiated workflow for technical founders. Both ship as **core, free, self-hosted features** — never held back for a paid tier. Self-hosting OpenGrow gets you the full product; hosted plans exist purely for convenience (no server to run, managed AI keys, priority support), never for extra functionality.

## Build order

OpenGrow is prioritizing the shortest path to a differentiated open-source workflow:

```
company context → generated content → GitHub PR → published URL → traffic → conversion → revenue
```

### Now: make the wedge visible
- Harden the tenant app shell: all authenticated pages remain under `/app/[slug]/...`
- Add frontend test harness depth around login redirect, pricing funnel, pages dashboard, and content editor flows
- Polish the pages/slugs dashboard into the primary workspace surface
- Harden in-app GitHub PR publishing UX: token configuration state, path/branch controls, PR metadata, publication history, and merge-to-`PUBLISHED` refresh are in place
- Keep Markdown export as the smallest useful publishing primitive

- Revenue event model, first-party tracking pixel/conversion capture, conversion examples, embed-code UX, tracking install status, deduped aggregate manual/GA4/GSC import, tenant attribution summary, time-windowed executive funnel metrics, charted previous-period trend deltas, per-content/source/channel trend charts, attribution recommendations, per-content cards, channel/source breakdowns, connector setup records, Google OAuth start URLs, callback token exchange, connector sync state, Google API row mapping, refresh-token renewal, and daily connector cadence are in place
- Attribution dashboard polish and richer executive attribution views
- **Revenue attribution** — next is final dashboard QA and then content calendar scheduling depth
- Basic content calendar focused on status and next action is in place; next is import-driven scheduling and channel-specific tasks

### Later: broaden channels
- WordPress, Ghost, Webflow adapters — **shipped** (via `POST /content/{id}/publish`); Hugo and plain HTML adapters next
- Social auto-post for X and LinkedIn — **shipped** (BYOK OAuth token)
- Email delivery — **shipped** (SMTP)
- API/webhook publishing for custom workflows
- SEO research and on-page scoring
- Technical SEO auditing

### Platform, after workflow proof
- First-class REST API — **shipped** (documented at `docs/API.md`, API keys, pagination)
- MCP server support, so OpenGrow can be driven directly from Claude Code, Cursor, or any other AI agent — **shipped** (`/mcp`)
- Per-tenant usage metering + rate-limiting mechanism — **shipped** (off by default)
- Usage-priced hosted API once real usage exists — pending (billing lives in the hosted tier)

## Deliberately delayed

- Full orchestrator agent before GitHub PR publishing works end-to-end
- Broad CMS/social integrations before the GitHub-native wedge converts users
- Treating GitHub PR publishing as the full product instead of the first channel
- Enterprise SSO before commercial demand exists
- Kubernetes before single-server hosted operations are proven
- Complex SEO crawler before attribution exists

## Guiding principle

Self-hosted and open source stays genuinely free — full feature set, not a crippled trial. Hosted plans sell convenience and infrastructure, never capability. If a feature is worth having, it's worth having for free.

## Open-source growth system

Every meaningful feature should produce:

1. GitHub issue with acceptance criteria
2. Pull request
3. Demo artifact
4. Documentation update
5. Release note
6. Build-in-public post
7. Follow-up issue for contributors

The internal maintainer operating plan tracks the launch calendar, marketing cadence, and private pricing experiments. Public contributors can use this section as the contribution and release standard.

## Timeline

No fixed dates yet — this is a nights-and-weekends project. Follow the repo for updates; the [CHANGELOG](https://github.com/opengrowhq/opengrow/commits/main) is the source of truth for what's actually shipped versus planned.

## Contributing

Interested in one of the items above? Open an issue or PR — see [AGENTS.md](./AGENTS.md) for repo conventions.

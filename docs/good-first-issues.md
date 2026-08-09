# Good first issue backlog

Curated, low-friction, high-recognition contributions. All are scoped to avoid
auth / tenancy / secrets / infra-heavy work, and reference `examples/` fixtures
where useful. Each entry below is ready to be filed as a `good first issue`.

> Maintainers: file these as issues with the `good first issue` label, pasting
> the acceptance criteria verbatim. Keep ~10 open at any time.

## Docs

1. **Add a "Troubleshooting lite" section to the README.**
   - AC: cover the top 4 lite gotchas (port conflicts, `EMBED_FAILED` when
     `nomic-embed-text` isn't pulled, stuck `SCANNING`/`EMBEDDING` = worker down,
     login 401 = not seeded). Link from Quick Start.
2. **Document `/version` and `/ready` in the API reference.**
   - AC: add both to `services/fastapi-core/docs/API.md` with example responses
     (`{"ready":true,"mode":"lite",...}`).
3. **Add alt text + captions to the README demo assets.**
   - AC: descriptive alt text for `docs/demo.gif` / `docs/demo.png`.

## Examples / fixtures

4. **Add a second brand-voice example for a different vertical.**
   - AC: `examples/brand-voice-<vertical>.txt` (e.g. e-commerce or agency),
     same shape as `brand-voice-founder-saas.txt`; reference it in
     `examples/README.md`.
5. **Add 2 more entries to `examples/content-briefs.json`.**
   - AC: valid briefs (match the existing schema/fields); topics distinct from
     the current three.
6. **Add a multi-currency variant of `revenue-events.csv`.**
   - AC: `examples/revenue-events-multicurrency.csv` with EUR/GBP rows; verify
     it imports via `make seed-demo`.

## Tests

7. **Unit-test the calendar bucketing logic.**
   - AC: cover Overdue/Today/Tomorrow/Later in
     `services/frontend/src/features/content/calendar.mjs` tests.
8. **Unit-test content origin labels.**
   - AC: extend `lineage.test.mjs` for generated vs article-draft vs manual.
9. **Add an analytics import schema edge-case test.**
   - AC: reject `revenue_cents < 0`; accept empty `content_piece_id`.

## Frontend (small states)

10. **Empty state for Analytics when there's no data.**
    - AC: friendly empty state (reuse `EmptyState`) instead of zeroed cards;
      no data fetch changes.
11. **Loading skeleton for the Settings page.**
    - AC: use the existing `Skeleton` while `/settings` data loads.

## Export templates / provider stubs

12. **Add a CMS export front-matter mapping example.**
    - AC: `docs/cms-export-mapping.md` showing OpenGrow content → Ghost and
      WordPress front-matter fields (mapping table, no live integration).

Each issue should be independently mergeable and require no real credentials.
Point contributors at the [ship checklist](./ship-checklist.md).

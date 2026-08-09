# Frontend tests

Two harnesses run side by side:

| Harness | Command | Scope | Files |
|---|---|---|---|
| `node --test` | `npm test` | Pure logic (framework-free) | `**/*.test.mjs` |
| Vitest + Testing Library (jsdom) | `npm run test:unit` | Component / interaction | `**/*.test.tsx` |

`npm run test:watch` runs Vitest in watch mode. Vitest only picks up `*.test.tsx`
and `node --test` only picks up `*.test.mjs`, so the two never overlap.

## Covered (component)

- **Auth redirect flow** — `features/auth/components/login-form.test.tsx`: submit
  → login mutation → post-auth redirect (incl. `?next=onboarding`), error state.
- **Generator studio** (Ads/Socials/Emails) — `features/studio/components/generator-studio.test.tsx`:
  the free-text brief is framed with the channel preset before calling the generation
  API, the result renders, save-to-library sends a channel-tagged title, and the
  no-brand hint shows. Guards the frontend-only channel presets over the generic API.

## Covered (pure logic, `*.test.mjs`)

Analytics helpers, content calendar/publish helpers, app-routes, first-paint, and the
studio channel presets (`features/studio/presets.test.mjs`).

## Known gaps (follow-ups)

- **Browser e2e** (Playwright) is not set up yet — no real backend-driven flow test.
  The component tests mock at the hook boundary. Add Playwright when a seeded lite
  stack is wired into CI.
- **Pricing checkout funnel** lives in the commercial hosted overlay (a separate,
  private repo), not here; its pure helpers are unit-tested there. Add component
  coverage for the toggle/checkout in that overlay using this same Vitest setup.

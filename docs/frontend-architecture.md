# OpenGrow Frontend — Architecture, UX & Onboarding

> **Status**: Living design/foundation doc. The scaffold (`services/frontend`,
> Next.js App Router + TS + Tailwind) exists with marketing, pricing, login, and
> a tenant app shell. This defines the target architecture and the migration path
> so every later phase slots into a stable core.
> **Audience**: contributors building the frontend. This doc is scoped to the
> open-source app's UI architecture.

---

## 1. Vision & principles

OpenGrow's UI is an **AI content growth cockpit**: brand in → generate → refine →
publish (GitHub-native) → measure → learn. It must feel fast, opinionated, and
delightful — the opposite of a dumped LLM textarea.

Design principles:

1. **Time-to-first-value < 5 min.** Paste a URL → see brand-aware content fast.
2. **Responsive & mobile-capable** — a deliberate wedge against desktop-only competitors. Every core flow works on a phone.
3. **Human-in-the-loop is a feature, not a chore** — inline editing, conversational refine, versioning, one-click regenerate. Editing should feel like collaboration, not cleanup.
4. **Publish in-app, no dead-ends** — content flows straight to a GitHub PR / channel. Never "download and figure it out yourself."
5. **No lock-in** — Markdown export everywhere; your content is portable.
6. **Accessible (WCAG 2.2 AA) and i18n-ready** from the start.
7. **Progressive disclosure** — power features exist but never block the first success.

---

## 2. Tech stack (frontend)

| Concern | Choice | Notes |
|---|---|---|
| Framework | **Next.js (App Router) + React + TypeScript** | RSC, streaming, file routing |
| Styling | **Tailwind v4** + design tokens | utility-first, tokenized theming |
| Components | **shadcn/ui** (Radix primitives) + a local component library | accessible, unstyled-primitive base |
| Server state | **TanStack Query** | caching, dedupe, pagination, optimistic updates |
| Client/UI state | **Zustand** (+ URL state, React state) | small, no boilerplate; see §6 |
| Forms | **React Hook Form + Zod** | typed validation shared with the API layer |
| Data viz | lightweight chart lib (analytics phase) | tree-shakeable |
| Component docs | **Storybook** | isolated component dev + visual review |
| Testing | Vitest + Testing Library (unit/component), Playwright (e2e) | + Storybook interaction tests |

All dependency choices follow the **latest-stable / zero-CVE** rule in `AGENTS.md`.

---

## 3. Feature-based architecture

Organize by **domain/feature**, not by file type. Each feature owns its
components, hooks, state, and API calls, exposing a small public surface via an
`index.ts`. This keeps encapsulation as the app grows and makes features
deletable/movable.

### Target structure

```
services/frontend/src/
├── app/                      # Next routes ONLY — thin; delegate to features
│   ├── page.tsx              # public marketing homepage
│   ├── pricing/              # public pricing + checkout funnel
│   ├── login/                # public auth form
│   └── app/[slug]/           # authenticated tenant surface
│       ├── page.tsx          # pages/slugs dashboard
│       ├── brand/
│       ├── content/
│       │   └── [id]/
│       └── onboarding/
├── features/                 # the real code lives here
│   ├── auth/                 # session, guards, login form, useSession
│   ├── brand/                # Brand DNA setup, profile editor, useBrand
│   ├── studio/               # generation: format picker, brief, review, refine
│   ├── content/              # content list, editor, lifecycle
│   ├── publishing/           # channels, GitHub publish, publications
│   ├── analytics/            # dashboards (later phase)
│   └── billing/              # plans, checkout, usage (later phase)
│       └── (each: components/  hooks/  api.ts  store.ts  types.ts  index.ts)
├── components/               # cross-feature UI primitives (design system)
│   └── ui/                   # button, input, dialog, sheet, toast, status-pill…
├── lib/                      # api client core, auth transport, query client, utils
├── hooks/                    # generic cross-cutting hooks
└── styles/                   # tokens, globals
```

### Migration from the current scaffold (small, do it early)

The scaffold is flat (`src/app/*`, `src/lib/api.ts`, `src/components/status-pill.tsx`).
Migrate incrementally:

1. Introduce `features/` and move auth + content code into `features/auth`,
   `features/content` (keep `lib/api.ts` split per-feature `api.ts` that re-use a
   shared `lib/http.ts`).
2. Keep authenticated routes under `app/[slug]/...` with a shared sidebar shell.
3. Add TanStack Query + Zustand (replace ad-hoc `fetch`/`useState`/polling).
4. Extract UI primitives into `components/ui` and document in Storybook.

Do this **before** building analytics/billing so those land on the stable core.

---

## 4. Rendering strategy (App Router)

Pick per route, not globally:

- **Marketing pages** (`(marketing)`): **SSG/ISR** — ultra-fast, SEO-critical, cached at the edge/CDN. `revalidate` for pricing/changelog.
- **Authenticated app** (`/app/[slug]/...`): mostly **client components** talking to the API via TanStack Query today (token in memory). Use **RSC + streaming (Suspense)** for shells and above-the-fold once auth moves to an httpOnly cookie (§7) so the server can fetch.
- **Onboarding**: client-driven (live progress), server shell for speed.
- Use **`loading.tsx` + Suspense** for skeletons; stream slow sections instead of blocking.

> Constraint today: auth token lives in `localStorage`, so server components
> can't fetch authed data (no cookie). Moving to a BFF-set httpOnly cookie (§7)
> unlocks RSC data fetching and better LCP. Track this as a core-phase task.

---

## 5. Component-driven UI & design system

- **Atomic layering**: tokens → primitives (`components/ui`, shadcn/Radix) → feature components → pages.
- **Design tokens** (Tailwind v4 `@theme`): color, spacing, radius, typography, elevation, motion. One source of truth; dark mode via tokens.
- **Storybook** for every primitive + key feature component (states: empty/loading/error/success), with a11y and interaction tests.
- Consistent **empty / loading / error** states are first-class (they're most of perceived quality).

### 5.1 Component patterns (conventions)

- **Presentational vs. Container**: presentational components take data via props
  and render UI only; data-fetching/state logic lives in a container or, more
  commonly here, a **custom hook** (`useBrand`, `useContent`) that the page/feature
  wires to a presentational tree. Keeps UI reusable and Storybook-able.
- **Compound components**: for cohesive widgets (Tabs, the Studio review gallery,
  the variant card set) share state implicitly between parent and children via
  React Context, so consumers compose (`<Review><Review.Card/></Review>`) without
  prop-drilling.
- **Controlled vs. uncontrolled**: forms are **controlled** via React Hook Form +
  Zod (validation, submit state); reach for **uncontrolled** (refs) only for
  perf-sensitive/large inputs (e.g. the long Markdown body) or file inputs.
- **Custom hooks**: the standard unit for reusing non-visual logic — data access
  (`useContent`), polling (`useJobStatus`), auth (`useSession`), and UI behavior
  (`useMediaQuery`, `useDebouncedValue`). Feature hooks live in
  `features/<name>/hooks/`; generic ones in `hooks/`.
- Keep components **pure and prop-driven**; push side effects to hooks. Prefer
  composition over configuration flags.

---

## 6. State management

Categorize state; don't over-globalize:

| Kind | Tool | Examples |
|---|---|---|
| Server/remote | **TanStack Query** | brand profile, content list, generation status (polling → later SSE), publications |
| Global client/UI | **Zustand** | session/user, theme, command-palette, active workspace |
| URL state | route/searchParams | filters, tabs, pagination, selected id |
| Local | `useState`/RHF | form inputs, toggles, wizard step |

Rules: server data is **never** copied into Zustand — Query owns it. Use
**optimistic updates** for lifecycle transitions and edits; **invalidate** on
mutation. Job progress (generation/publish/video): poll via Query today,
migrate to **SSE/WebSocket** when the backend adds it.

---

## 7. Auth & data transport

- **Now (scaffold)**: token in `localStorage`, `Authorization: Bearer` header, CORS from the API. Fine for lite/dev.
- **Target**: BFF (`node-gateway`) sets an **httpOnly, SameSite cookie**; the browser never holds the token; RSC and route handlers can fetch server-side. Add CSRF protection for cookie mode. This is a **core-phase** item — it improves security *and* rendering.
- One typed HTTP layer (`lib/http.ts`) with interceptors (auth, refresh, error normalization); per-feature `api.ts` builds on it; response types shared with backend via generated types or hand-kept Zod schemas.

---

## 8. Performance / Core Web Vitals

Targets: **LCP < 2.5s, INP < 200ms, CLS < 0.1** (field data).

- **Code splitting**: route-level automatic; `next/dynamic` for heavy, below-fold, or rarely-used components (editor, charts, video preview).
- **Assets**: `next/image` (responsive, lazy, modern formats); self-host fonts via `next/font` (no layout shift); Brotli/GZIP; defer non-critical JS/CSS.
- **Lazy loading**: Intersection Observer / `next/dynamic` for off-screen; **prefetch** likely-next routes (`<Link prefetch>`), preload critical data.
- **Streaming RSC**: send shell immediately, stream data — big LCP win once on cookie auth.
- **Caching**: TanStack Query client cache + HTTP caching; CDN/edge for static + ISR pages.
- Budget: track bundle size in CI; fail on regressions. Measure with Lighthouse CI + real-user vitals (`web-vitals` → our own analytics, no third-party).

---

## 9. The UX — screens & flows (beating Holo)

Holo's flow: URL → swipe ideas → edit → **download & publish**. We keep the fast,
delightful bits and fix the dead-ends.

### 9.1 Onboarding (the make-or-break)
Chrome-less, ≤5 steps, resumable, with a live progress feel:

1. **Sign up** (email or OAuth) — one field to start.
2. **Paste your URL** — kick off Brand DNA extraction; show **live progress** across sections (Core Basics · Market · Brand Voice · Visual Style) with streaming updates, not a spinner.
3. **Review & tweak brand** — editable cards (tone, palette, audience, do/don't); "looks right?" confirm. Never a wall of empty forms.
4. **First generation** — pre-filled brief from the brand → produce 3–5 variants **in the onboarding itself** (the "aha").
5. **Land in the app** with a **setup checklist** (connect a publish channel, invite a teammate) — progressive, dismissible.

Beat Holo: **works on mobile**, resumable, and the first *publish* (not just download) is one click away.

### 9.2 App shell
Left **sidebar** (Home, Ads, Socials, Emails, Library, Brand DNA) plus a bottom-left OpenGrow account/workspace popover. Canonical app pages live under `/app/[slug]/...`; top-level `/brand`, `/content`, and `/onboarding` are not app URLs.

### 9.3 Dashboard / Home
"What now" surface: pages/slugs dashboard with setup checklist, recent pages + statuses, quick-create by intent, usage/credits, and (later) top-performing content by revenue.

### 9.4 Studio (generation)
- **Format picker** (ad / social / email / blog / image / video) → **brief** (pre-filled from brand) → variant count.
- **Review** generated variants: a **gallery + swipe/keyboard** pattern (accept/skip/compare) — better than Holo's one-at-a-time-only: multi-select, side-by-side, keyboard shortcuts, undo.
- **Refine**: conversational editor ("make the headline punchier") **plus** direct inline editing and a **version history** — not chat-only.
- Every accepted variant → **"Save as content"** → the content lifecycle.

### 9.5 Content
List (filter by status/format/campaign) → **editor** (title/body, planning metadata, live Markdown preview, status machine, export, publish). The calendar view groups content by due date and next action.

### 9.6 Publish / Channels
GitHub PR publishing is the first channel. The content editor checks backend
configuration (`/content/publish/github/config`), lets the user pick target
repo/path/base branch/publish branch, accepts commit + PR metadata, opens the PR
in-app, tracks **Publications** with status plus the real PR link, and can
refresh a PR after merge to mark the publication/content as `PUBLISHED`. Later:
automatic webhook/polling refresh, WordPress/Ghost/social.

### 9.7 Analytics (active foundation)
Per-content performance starts with protected revenue event import, aggregate
manual/GA4/GSC import from the app dashboard, tenant summary metrics, top
content cards, normalized channel cards, and source URL breakdowns. Repeated
imports use backend dedupe keys so refreshed connector rows do not double-count.
The dashboard can store GA4/GSC connector setup records and request a Google
OAuth start URL when the backend is configured, then submit the returned code to
complete the connector. Connected connectors expose sync state and a manual sync
trigger. Backend sync fetches GSC page rows and GA4 landing-page rows into
deduped attribution events, refreshes Google access tokens when possible, and is
queued daily by Celery beat. First-party visit and conversion capture is
available through public pixel/track endpoints, with dashboard embed snippets for
workspace or per-page installs, install-state checks, and selectable conversion
examples. The workspace dashboard derives executive funnel metrics from
time-windowed tenant summary data and renders recommendation cards from
attribution signals. Previous-period trend deltas compare the selected window
against the immediately preceding window and render paired current/previous bars.
Content, source, and channel cards include compact current/previous trend bars.
Next: final dashboard QA, then content calendar scheduling depth.

### 9.8 Billing / Settings (later phase)
Plans + the bottom-sheet Stripe checkout, usage & rollover credits, one-click cancel; workspace, members, brand, API keys (BYOK), theme.

---

## 10. Accessibility & i18n

- WCAG 2.2 AA: keyboard-navigable, focus management (dialogs/sheets), ARIA via Radix, color-contrast tokens, reduced-motion.
- i18n-ready structure (Holo advertises 99+ languages): externalize copy, `next-intl`-style routing, locale-aware formatting — even if we ship English first.

---

## 11. Testing

- **Unit/component**: Vitest + Testing Library.
- **Current lightweight layer**: `npm test` runs focused Node tests for route helpers, GitHub publish form defaults, and other framework-independent contracts.
- **Storybook**: stories per primitive + interaction/a11y tests; visual regression.
- **E2E**: Playwright over the critical paths (onboarding → generate → save → approve → export/publish) against the lite stack.
- CI gates: typecheck, eslint, unit + a11y, Lighthouse CI budget, Playwright smoke.
Every new or changed UI functionality must include focused tests in the same change. If the full browser harness is not in place, add the closest useful lower-level test and document the gap.

---

## 12. Monorepo tooling & micro-frontends — deliberately minimal now

**Monorepo tooling (Turborepo / Nx): not yet.** The repo is already a multi-service
monorepo (`services/*`), but with one frontend app the overhead of Nx/Turborepo
(task graphs, generators, caching config) isn't justified. The one thing worth
sharing across the frontend and the `node-gateway` BFF is **types** (API
request/response shapes) — solve that first with a lightweight shared package or
generated types (openapi-typescript), not a full monorepo framework. Adopt
Turborepo only when there's a second app or a shared UI library that multiple
apps consume; the feature-based structure keeps that migration cheap.

**Micro-frontends: no.** Single small team + one cohesive product → a **modular
monolith** (feature-based Next app) is correct. Micro-frontends (Module
Federation, runtime composition) add build/integration/runtime cost that isn't
justified. Revisit only if independent teams need independent deploy cadences
(e.g. a separate analytics org). §3's structure keeps that door open without
paying the cost now.

---

## 13. Phased frontend roadmap (maps to the wedge)

| Phase | Deliverable |
|---|---|
| **F0 — Core (now)** | TanStack Query (replaces hand-rolled fetch/poll) + light feature-based reorg. Cookie-auth via BFF as the next core item. **Defer** Zustand + Storybook until they earn their place (see note). |
| **F1 — Onboarding + Brand** | URL → live Brand DNA extraction UX, review/edit, setup checklist |
| **F2 — Studio** | Format picker → brief → variant review (gallery/swipe) → conversational + inline refine + versions |
| **F3 — Content + Publish** | Editor polish, in-app GitHub publish UX, publications tracking (builds on scaffold) |
| **F4 — Analytics** | Performance dashboards → revenue attribution |
| **F5 — Billing/Team** | Bottom-sheet Stripe checkout, usage/credits, members/roles |

> **Staging note (why F0 is trimmed):** TanStack Query is a clear win now — it
> replaces hand-rolled `fetch` + `useState` + `setTimeout` polling with caching,
> dedupe, and declarative refetch. Zustand and Storybook are **deferred on
> purpose**: we have ~no global client state (a tiny `auth.ts` module suffices)
> and only a couple of components, so adding them now is cost without payoff —
> exactly the "don't over-globalize / match the tool to the use case" principle.
> Introduce Zustand *with* the first real global state (workspace switcher /
> command palette) and Storybook *with* a real component library or a second
> contributor.

Ordering stays consistent with the backend **wedge-first** plan: the
content→publish path is the spine; Studio media and analytics layer on after.

---

## 14. Open items / decisions to make

- Generated API types (openapi-typescript from FastAPI `/openapi.json`) vs hand-kept Zod schemas — pick one and automate.
- SSE vs WebSocket for job progress (currently polling).
- Chart lib choice (analytics phase).
- Confirm cookie-auth CSRF strategy with the BFF.

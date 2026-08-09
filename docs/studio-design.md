# Studio — Multi-Modal Generation Design

> **Status**: Living proposal / design doc. Backend content and brand primitives
> plus the first Next.js frontend shell exist; multi-modal generation remains
> proposed.
> **Goal**: Extend OpenGrow from text-only generation into a **Studio** surface
> that produces brand-aware marketing **text, images, and video** — while staying
> inside the existing architecture and invariants (`AGENTS.md`, `ASSUMPTIONS.md`).
>
> Scope note: this doc is the **technical build spec**. Product/pricing/tier
> decisions (what's free vs hosted-only) are intentionally out of scope here and
> tracked separately by the maintainers.

---

## 1. Feature scope

| Capability | Today | Work |
|---|---|---|
| Brand profile — scrape a site → tone, palette, messaging, audience | Assets + embeddings exist; no extraction | New `Brand` domain + scraper worker |
| Copy generation (ads / social / email), brand-conditioned | `Generation` (text-only) | Format taxonomy + brand injection |
| Multi-variant output | Single string result | Structured multi-variant text |
| Image / ad-creative generation | None | Extend LiteLLM gateway + image worker |
| Video / avatar generation | None | New media gateway + poll/webhook worker |
| Asset library / campaigns | Assets exist, no grouping | `Campaign` model + presigned URLs |
| Usage metering + concurrency limits | None | Credit ledger + concurrency cap |
| Web UI | Next.js shell exists | Expand Studio workflows inside `/app/[slug]/...` |

Everything below reuses OpenGrow's existing primitives — `202 → poll`, Celery
queues, MinIO Assets, OpenFGA ReBAC, the LiteLLM gateway, tenant isolation —
rather than introduce parallel machinery.

---

## 2. Core architectural decision: generalize `Generation`

`app/models/generation.py` is currently **text-only**: one `result: Text`
column, and `run_generation` (`app/workers/tasks.py:156`) always calls
`chat_completion` and writes a string.

**Decision:** widen `Generation` into a **multi-modal content record** instead of
creating parallel `ImageGeneration` / `VideoGeneration` tables. One resource,
one authz binding, one status-poll flow.

### 2.1 New/changed columns on `Generation`

```python
class GenerationKind(str, enum.Enum):
    TEXT  = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"

class GenerationStatus(str, enum.Enum):   # extend existing
    QUEUED           = "QUEUED"
    RUNNING          = "RUNNING"
    RENDERING        = "RENDERING"          # NEW: media provider working
    PROVIDER_POLLING = "PROVIDER_POLLING"   # NEW: long video job, polling
    COMPLETE         = "COMPLETE"
    FAILED           = "FAILED"

# added columns
kind:             GenerationKind            # routes to worker + provider
format:           str | None                # e.g. tiktok_ad, ig_post, email_seq, ugc_video
brand_id:         UUID | None  -> brands.id # replaces the ad-hoc ref_hint
output_asset_ids: JSONB (list[str])         # media outputs stored as Assets
variant_count:    int = 1                   # multi-variant text/image
cost_units:       int = 0                   # metered usage (see §8)
# result: Text stays — used for TEXT kind only
```

`reference_asset_id` stays for backward-compat but `brand_id` becomes the primary
conditioning input.

### 2.2 Alembic migration
One migration: new enum type `generation_kind`, new enum values on
`generation_status`, new columns (all nullable / defaulted so it is backward
compatible). New tables `brands`, `campaigns`, `usage_ledger` (below).

---

## 3. New domains

### 3.1 `Brand` (brand profile)

`app/models/brand.py`:

```python
class BrandStatus(str, enum.Enum):
    PENDING    = "PENDING"
    SCRAPING   = "SCRAPING"
    EXTRACTING = "EXTRACTING"
    READY      = "READY"
    FAILED     = "FAILED"

class Brand(TenantMixin, Base):
    __tablename__ = "brands"
    owner_id:    UUID -> users.id
    name:        str
    source_url:  str | None
    status:      BrandStatus
    profile:     JSONB   # {tone, palette:[#hex], tagline, audience, pains,
                         #  do_phrases:[], dont_phrases:[], logo_asset_id}
    error_message: str | None
```

**Worker** `build_brand_profile(brand_id)` on `cpu_light`:
1. Fetch `source_url` with `httpx` (add dep) + extract readable text with
   `trafilatura` or `selectolax` (no headless browser for v1).
2. Parse colors from inline styles / CSS / `<meta name="theme-color">`.
3. Call `chat_completion` with a **JSON-schema system prompt** → structured
   `profile`. (Keeps the "LLM only through LiteLLM" invariant.)
4. Optionally download logo/hero image → store as an Asset → `logo_asset_id`.
5. `status = READY`.

**Endpoints** `app/routers/brands.py` (prefix `/brands`):
- `POST /brands` → `202`, enqueues `build_brand_profile` (authz `writer` on tenant).
- `GET /brands/{id}` → status + profile (authz `reader`).
- `GET /brands` → list for tenant.
- `PATCH /brands/{id}` → manual profile edits (users refine the auto-extraction).

### 3.2 `Campaign` (grouping)

`app/models/campaign.py` — `Campaign(TenantMixin)` with `name`, `brand_id`,
`description`. `Generation` gets optional `campaign_id`. Gives the UI "projects."

### 3.3 `UsageLedger` (metering mechanism)

`app/models/usage.py`:
```python
class UsageLedger(TenantMixin, Base):     # append-only
    generation_id: UUID
    kind:          GenerationKind
    cost_units:    int
    balance_after: int
```
This is the **mechanism** only — units, balances, enforcement. Any monetary
mapping / plan policy is a hosting-operator concern, not part of this spec.

---

## 4. Provider / gateway layer

### 4.1 Text — no new gateway
Reuse `app/core/litellm_client.py::chat_completion`. Add `app/core/prompts/`
with per-format templates. Multi-variant = ask for a JSON array of N variants;
store in `result` (TEXT) as JSON.

### 4.2 Images — **extend** the LiteLLM gateway (preserve invariant)
Add to `app/core/litellm_client.py`:
```python
async def image_generation(prompt, model="flux-schnell", size="1024x1024",
                           n=1) -> list[bytes]:
    # library mode: litellm.aimage_generation(...)
    # proxy mode:   POST {LITELLM_URL}/images/generations
```
Add to `infra/litellm/config.yaml`:
```yaml
  - model_name: flux-schnell
    litellm_params:
      model: fal_ai/fer-flux/schnell        # or replicate/black-forest-labs/flux-schnell
      api_key: os.environ/FAL_KEY
  - model_name: dall-e-3
    litellm_params:
      model: openai/dall-e-3
      api_key: os.environ/OPENAI_API_KEY
```
This keeps the AGENTS.md invariant: **no provider SDK imported in app code.**

### 4.3 Video — **new** `media_client.py` gateway
LiteLLM does not cleanly abstract video providers, and video jobs are **long
(minutes) and async on the provider side**. So add ONE new gateway module (same
spirit as the LiteLLM invariant: a single choke point, not scattered imports).

`app/core/media_client.py`:
```python
async def submit_video_job(prompt, brand, model="fal_ai/kling-video", ...) -> str:
    """Returns a provider job id. Does NOT block."""
async def poll_video_job(job_id) -> {"status", "url" | None}:
async def fetch_bytes(url) -> bytes:
```
**Start with an aggregator** (fal.ai or Replicate) that fronts multiple video
models behind one API — avoids integrating each provider separately. Provider
choice lives in config and is swappable without app changes (also insulates us
from provider churn — models get sunset regularly).

---

## 5. Queues & workers

Current: `cpu_light`, `gen_heavy`. **Add `gen_media`** so a stuck multi-minute
video render never starves image/text jobs.

| Worker | Queue | Kind |
|---|---|---|
| `build_brand_profile` | `cpu_light` | Brand profile |
| `run_generation` (text) | `gen_heavy` | Text |
| `run_image_generation` | `gen_heavy` | Image |
| `submit_video_generation` | `gen_media` | Video (submit) |
| `poll_video_generation` | `gen_media` | Video (self-re-enqueue `countdown=15` until terminal) |

`run_generation` becomes a **dispatcher**: switch on `gen.kind` →
text / image / video path. Media paths: call gateway → `fetch_bytes` → store as
an Asset in the assets bucket → append to `output_asset_ids` → `COMPLETE` →
`notify_email`.

Video completion via **either** polling (lite-safe) **or** provider webhook →
new `POST /generations/{id}/callback` (public URL via Caddy; guard
`if not settings.is_lite`).

Compose: add a `celery-media` worker service (or route `gen_media` on the
existing `celery-heavy`). Update `docker-compose.yml` + `docker-compose.lite.yml`
(lite runs all queues on the single worker).

---

## 6. API surface (all `get_current_user` + `authz_client.check`)

```
POST   /brands                      202  build brand profile
GET    /brands            /{id}          list / status+profile
PATCH  /brands/{id}                      refine profile
POST   /campaigns         /{id}          group generations
POST   /generations                 202  now takes {kind, format, brand_id, brief, variant_count, model}
GET    /generations/{id}                 status + result + output_asset_ids
GET    /generations/{id}/callback        (video webhook; prod only)
GET    /assets/{id}/url                   presigned GET (needed to show media)
GET    /usage                             usage balance + ledger
```

`create_generation` (`app/routers/generations.py:19`) gains: usage + concurrency
**pre-check before enqueue**, and `brand_id` authz check (reader on the brand).

---

## 7. Two-mode behavior (lite vs production) — mandatory per AGENTS.md

| Concern | Lite | Production |
|---|---|---|
| Provider keys | env vars (`FAL_KEY`, etc.) | Infisical |
| Image/video | direct provider calls via LiteLLM library + `media_client` | LiteLLM proxy + `media_client` |
| Video completion | **polling only** (no public URL) | polling **or** webhook via Caddy |
| Usage metering | balance tracked, enforcement optional | enforced |
| Generated-media AV scan | skipped | optional (machine-generated) |
| Qdrant brand retrieval | skipped (as today) | enabled |

---

## 8. Usage metering & concurrency (mechanism)

- Relative `cost_units` per kind (tune to real provider prices): TEXT ≈ 1,
  IMAGE ≈ 10, VIDEO ≈ 200.
- Enforce **before enqueue** in the router; write `UsageLedger` row after
  provider cost is known (video cost finalized on completion).
- **Concurrency cap** via a Redis counter keyed by tenant; increment on enqueue,
  decrement on terminal state.
- How units map to money / plans / limits is a **hosting-operator policy**,
  deliberately not encoded here — self-hosters set their own.

---

## 9. Frontend — current shell and gating work

There is now a **Next.js** (TypeScript) frontend with public marketing/pricing,
login, and an authenticated tenant shell. The canonical app surface is
`/app/[slug]/...`; do not add protected product pages at top-level paths such as
`/brand`, `/content`, or `/onboarding`.

Minimum Studio screens:
1. **Pages/slugs dashboard** — primary workspace surface at `/app/[slug]`, with page status, quick-create, setup checklist, attribution cards, normalized channel cards, source breakdowns, connector setup, and deduped aggregate metric import.
2. **Brand setup** — `/app/[slug]/onboarding` and `/app/[slug]/brand`; paste URL → watch brand profile build → review/edit.
3. **Publish** — content editor can open GitHub PRs with repo/path/branch/PR metadata and publication history.
4. **Create** — pick format (ad/social/email/image/video) → brief → variant count → generate.
5. **Gallery** — campaign-grouped assets with presigned previews, download, regenerate.
6. **Usage** — balance + history.

The remaining Studio UX is still one of the largest chunks of the effort. Every
new UI behavior must ship with focused tests; until the full browser harness is
added, use the closest lower-level test coverage.

---

## 10. Phasing (value-to-effort order)

| Phase | Deliverable | Notes |
|---|---|---|
| **P1** | Generalize `Generation` (kind/format/output_asset_ids) + `Brand` profile + multi-format text | Highest value, reuses everything, cheap to run. Branch `feature/studio-brand-profile`. |
| **P2** | Image generation via LiteLLM gateway extension | Fits `gen_heavy` cleanly |
| **P3** | Expand frontend Studio UI | Builds on the existing `/app/[slug]` shell |
| **P4** | Usage metering / concurrency limits | Protects against runaway cost |
| **P5** | **Video generation** | Last: highest cost, longest jobs, needs P4 metering + moderation first |

---

## 11. Risks & caveats

- **Video is its own sub-project** — difficulty is ops (long async jobs, cost
  per render, moderation, retries), not AI. Ship it only after metering (P4).
- **Cost blast radius** — one unbounded "generate video" button can burn real
  money fast. Concurrency cap + pre-flight usage check are non-negotiable before P5.
- **Content moderation** — generated ads/faces need a provider moderation pass +
  an acceptable-use policy before any public/hosted exposure.
- **Provider churn** — video/image models get sunset regularly; the
  `media_client` abstraction is what protects us from that.

---

## 11a. Dependency freshness (per AGENTS.md CVE policy)

Studio adds several deps and providers — all subject to the dependency-freshness
invariant in `AGENTS.md`:

- New Python deps (`httpx`, an HTML text extractor like `trafilatura` /
  `selectolax`, any provider client pulled transitively): install the **latest
  stable** release at implementation time, verified zero-CVE via `pip-audit`.
  Do not copy version numbers from this doc — resolve them fresh.
- Image/video **model providers** and aggregators (fal.ai / Replicate / etc.):
  prefer actively-maintained APIs and current model IDs; provider/model names in
  §4 are illustrative, not pinned — confirm the live, non-deprecated ID when wiring.
- `litellm` and the LLM/media gateway path: keep on the latest stable (it moves
  fast and ships security/compat fixes frequently).
- Any new container (e.g. `celery-media`) uses the same latest-stable base image
  policy as the rest of the stack.

## 12. Security checklist (per AGENTS.md — every PR in this effort)

- [ ] Every new endpoint (`/brands`, `/campaigns`, `/usage`, callback) uses `get_current_user`
- [ ] Every query filters by `tenant_id`; new models extend `TenantMixin`
- [ ] Every mutation/read calls `authz_client.check`; resources bound via `bind_resource_to_tenant`
- [ ] No `openai`/`anthropic`/provider SDK imports outside `litellm_client.py` / `media_client.py`
- [ ] Provider keys from Infisical (prod) / env (lite) — never in git
- [ ] Brand `source_url` fetch is **SSRF-guarded** (block internal IPs / cloud metadata endpoints / non-http schemes)
- [ ] Generated media stored tenant-prefixed in MinIO; presigned URLs expire
- [ ] Usage check + concurrency cap enforced before enqueue
- [ ] Pydantic validation on all new schemas; `format` allowlist
- [ ] New deps/providers are latest-stable, maintained, zero open CVEs (see §11a)

---

## 13. Files touched (index)

**New**
```
app/models/brand.py, campaign.py, usage.py
app/schemas/brand.py, campaign.py, usage.py
app/routers/brands.py, campaigns.py, usage.py
app/core/media_client.py
app/core/prompts/               # format templates
app/workers/  build_brand_profile, run_image_generation, submit/poll_video_generation
alembic/versions/xxxx_studio.py
services/frontend/src/app/app/[slug]/   # tenant-scoped Next.js app routes
```
**Changed**
```
app/models/generation.py        # kind, format, brand_id, output_asset_ids, statuses, cost_units
app/schemas/generation.py       # GenerationCreate/Out widened
app/routers/generations.py      # dispatcher + usage/concurrency pre-check
app/workers/tasks.py            # run_generation → dispatcher; media workers
app/core/litellm_client.py      # + image_generation
infra/litellm/config.yaml       # image models
docker-compose*.yml             # celery-media / gen_media queue
app/main.py                     # register brands/campaigns/usage routers
ASSUMPTIONS.md, AGENTS.md       # doc cadence
```

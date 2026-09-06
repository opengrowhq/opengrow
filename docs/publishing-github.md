# Publishing to GitHub (pull-request workflow)

OpenGrow's first publishing channel opens your approved content as a **pull
request** on a GitHub repo — so website and docs content flows through the same
reviewable PR process your team already trusts. This is a **bring-your-own-key
(BYOK)** workflow: you provide a GitHub token, OpenGrow uses it to write the file
and open the PR.

> Self-hosting sets one token for the whole instance (you own it).
> Multi-tenant deployments can instead let each workspace connect its own
> GitHub separately — see §"Per-tenant token" below.

## 1. Pick (or create) a target repo

Any repo you can write to — e.g. your website/docs repo, or a throwaway
`your-org/blog` to try it out. OpenGrow never force-pushes; it writes to a new
branch and opens a PR against your base branch.

## 2. Create a GitHub token

**Recommended — fine-grained personal access token** (scoped to just the repos you publish to):

1. Go to **GitHub → Settings → Developer settings → Personal access tokens →
   Fine-grained tokens** ([direct link](https://github.com/settings/personal-access-tokens)).
2. **Generate new token.**
3. **Token name:** e.g. `opengrow-publishing`.
4. **Expiration:** your call (shorter is safer; you can regenerate).
5. **Resource owner:** the account or org that owns the target repo.
6. **Repository access → Only select repositories** → choose your target repo(s).
7. **Permissions → Repository permissions:**
   - **Contents:** Read and write
   - **Pull requests:** Read and write
   - *(Metadata: Read-only — added automatically.)*
8. **Generate token** and copy the `github_pat_…` value (shown once).

**Classic PAT alternative:** a classic token with the **`repo`** scope also works
(broader access — prefer fine-grained when you can).

> ⚠️ **Fine-grained tokens on org-owned private repos:** a fine-grained PAT
> will `404` (as if the repo doesn't exist) unless **all** of these hold:
>
> 1. **Resource owner** (step 5) is the **organization** — not your personal
>    account. A token owned by you cannot see the org's private repos, even if
>    you're a member.
> 2. The repo is explicitly listed under **Only select repositories**.
> 3. An **org owner has approved** the token — orgs with "Require approval for
>    fine-grained personal access tokens" enabled (the safe default) keep the
>    token pending until then. Check **GitHub → your org → Settings →
>    Personal access tokens → Pending requests** if the API keeps 404ing.
>
> If any of these is blocked (e.g. you're not an org owner), fall back to a
> classic `repo` PAT from an account with access.

## 3. Configure OpenGrow

**Lite / self-host:** put the token in your `.env`:

```bash
GITHUB_TOKEN=github_pat_xxxxxxxx
# optional, for GitHub Enterprise Server:
# GITHUB_API_URL=https://github.your-company.com/api/v3
```

Then restart the app so it picks up the env var:

```bash
docker compose -f docker-compose.lite.yml up -d --force-recreate fastapi-core celery-worker
```

**Production:** store `GITHUB_TOKEN` in Infisical instead of `.env` (same key).

Verify it's live:

```bash
curl -s localhost:8000/content/publish/github/config \
  -H "Authorization: Bearer $TOKEN" | jq
# → {"configured": true, "api_url": "https://api.github.com",
#    "source": "env", "has_tenant_credential": false, "token_last4": null}
```

**Per-tenant token (multi-tenant deployments):** instead of one instance-wide
`GITHUB_TOKEN`, each tenant can store its own PAT — encrypted at rest, never
returned by the API:

```bash
# store or replace the tenant token (validated against GitHub before saving)
curl -X POST localhost:8000/content/publish/github/credentials \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"token": "github_pat_xxxxxxxx", "display_name": "Blog repo PAT"}'
# → {"configured": true, "source": "tenant", "token_last4": "xxxx", ...}

# remove it (publishing falls back to GITHUB_TOKEN if set)
curl -X DELETE localhost:8000/content/publish/github/credentials \
  -H "Authorization: Bearer $TOKEN"
```

When a tenant token is stored it wins over `GITHUB_TOKEN`; the config endpoint
reports which one is in effect via `source` (`"tenant"` / `"env"` / `null`).

## 4. Publish a piece

1. In the app, open a content piece and move it through **Draft → In review →
   Approved** (publishing is blocked until it's approved).
2. In the **GitHub publish** panel, fill:
   - **Repo** — `owner/repo`
   - **Path** — where the Markdown file lands, e.g. `content/my-post.md`
   - **Base branch** — defaults to the repo default (e.g. `main`)
   - Optional: branch name, commit message, PR title/body
3. Publish. OpenGrow writes the Markdown to a new `opengrow/{content_id}` branch
   and **opens (or reuses) a pull request** against the base branch.
4. Review and merge the PR on GitHub as usual.
5. Back in OpenGrow, hit **Refresh status** on the publication — once the PR is
   merged, the publication and the content piece flip to **`PUBLISHED`**.

The same flow is available headlessly: `POST /content/{id}/publish/github`
(see [`services/fastapi-core/docs/API.md`](../services/fastapi-core/docs/API.md)).

## Security notes

- The token is a secret. Keep it in `.env`/Infisical, never in the repo.
- Scope it to only the repos you publish to (fine-grained), and rotate it if leaked.
- In lite mode the token is instance-wide — fine for a single owner. Don't share a
  lite instance's token across untrusted users.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `configured: false` | `GITHUB_TOKEN` not set / app not restarted after setting it. |
| `GitHub publishing not configured — set GITHUB_TOKEN.` | Same — set the env var and recreate the containers. |
| `403` / "Resource not accessible" | Token lacks **Contents** or **Pull requests: write**, or the repo isn't in the token's selected repositories. |
| `404` on the repo | Wrong `owner/repo`, or the token's resource owner can't see it. On an **org-owned private repo** with a fine-grained token, see the warning in §2 — owner must be the org, repo selected, org-owner approval granted. |
| "Approve before publishing" | Move the piece to **Approved** first. |

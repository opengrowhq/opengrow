# GitHub Discussions setup

Start community here before Discord — lower overhead, searchable, tied to the
repo. This doc defines the categories and seed posts; enabling Discussions and
creating the posts are one-time maintainer actions in the GitHub UI.

## Enable

Repo **Settings → General → Features → Discussions** (checkbox). Or via the API:

```bash
gh api -X PATCH repos/opengrowhq/opengrow -f has_discussions=true
```

## Categories

Create these (delete the defaults you don't want):

| Category | Format | Purpose |
|---|---|---|
| **Show and tell** | Open | Users share what they published/automated with OpenGrow |
| **Content workflows** | Q&A | Briefs, outlines, brand voice, generation quality |
| **Publisher integrations** | Q&A | GitHub PR publishing + future channels (WordPress, Ghost, Webflow…) |
| **Self-hosting help** | Q&A | Lite/production deploy, Docker, backups, upgrades |
| **Roadmap feedback** | Open | What to build next; reactions triage priority |

## Seed posts (one per category)

- **Show and tell** — "Show us your first OpenGrow-published post" — invite a
  before/after with the merged PR link.
- **Content workflows** — "How are you structuring briefs?" — link
  `examples/content-briefs.json` and the [demo walkthrough](./demo-walkthrough.md).
- **Publisher integrations** — "Which channel should we add next?" — list the
  candidates (WordPress, Ghost, Webflow, email, social) and ask for reactions.
- **Self-hosting help** — "Lite vs production: which should I run?" — link the
  [threat model](./threat-model.md) and [backup/restore](./backup-restore.md).
- **Roadmap feedback** — "What's the one thing that would make OpenGrow a
  daily tool for you?" — link [ROADMAP.md](../ROADMAP.md).

## Maintainer notes

- Convert recurring Q&A answers into `docs/` pages or FAQ entries.
- Link Discussions from the README once seeded.
- Use the [maintainer response template](./hacktoberfest.md#2-maintainer-response-template)
  for a fast, consistent first reply.

# Hacktoberfest preparation

Prep by **September** so October runs smoothly: a stocked backlog of small,
well-specified issues, a fast maintainer response, and a plan to recognize
contributors.

## 1. Backlog — 20 ready issues

File these with the `hacktoberfest` label (and `good first issue` where they
overlap). All are small, have exact acceptance criteria, and need **no real
secrets**. Start from the [good-first-issue backlog](./good-first-issues.md)
(12 issues) plus the 8 below:

13. **Add `docs/faq.md`** — 8–10 Q&As from README/threat-model content.
14. **Add a `make lite-reset` target** — `lite-down` + volume prune + `lite-up`
    + migrate + seed, documented in the Makefile help.
15. **Add copy-to-clipboard buttons** to the tracking snippets in the Analytics
    tracking panel.
16. **Add a favicon/OG-image check to the docs** — document the existing
    `manifest.ts` / `opengraph-image` setup.
17. **Improve `examples/README.md`** — one line per fixture describing shape +
    which endpoint consumes it.
18. **Add a `CODE_OF_CONDUCT.md`** (Contributor Covenant) and link from
    CONTRIBUTING.
19. **Add a channel-breakdown empty state** to the Analytics breakdown table.
20. **Document the orchestrator run states** (`AWAITING_OUTLINE_APPROVAL`, …) in
    the API reference.

Each issue must be independently mergeable and CI-green on its own.

## 2. Maintainer response template

Speed of first response is the single biggest driver of a good Hacktoberfest.
Aim for < 24h.

> Thanks for picking this up, @contributor! 🎉
>
> Assigning it to you. Quick pointers:
> - Setup: `make lite-up && make lite-migrate && make lite-seed` (see
>   [CONTRIBUTING](../CONTRIBUTING.md)); seed demo data with `make seed-demo`.
> - Scope: just the acceptance criteria above — smaller is better.
> - Include a focused test and a line in `CHANGELOG.md` (see the
>   [ship checklist](./ship-checklist.md)).
>
> Ping me here if anything's unclear — happy to help you land it.

For out-of-scope or spammy PRs, respond kindly and label `invalid`/`spam` per
Hacktoberfest rules.

## 3. Contributor recognition plan

- [ ] Add a **Contributors** shout-out section to the October release notes
      (@-mention every merged author).
- [ ] Thank each contributor on the PR at merge and in the build-in-public post.
- [ ] Track first-time contributors and invite standout ones to take a larger
      issue next.

## 4. Readiness checklist

- [ ] ≥ 20 `hacktoberfest` issues open with exact AC and no secret deps.
- [ ] Demo data reproducible via `make seed-demo`.
- [ ] Maintainer response template pinned/saved.
- [ ] Recognition section drafted in the release notes template.

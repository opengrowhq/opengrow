# Ship checklist (build-in-public)

Every shipped feature should leave a visible trail. Before closing the issue or
merging the feature, confirm each artifact exists. Copy this list into the PR
description (or use the `ship-checklist` issue template).

## The checklist

- [ ] **Demo artifact** — a GIF, screenshot, or terminal capture showing the
      feature working end-to-end (drop it in `docs/` and link it).
- [ ] **Docs update** — README and/or a `docs/*.md` page reflect the change;
      the [REST API reference](../services/fastapi-core/docs/API.md) updated
      if endpoints changed.
- [ ] **Tests** — focused tests for the new/changed behavior (per the repo
      [testing rule](../README.md#testing-rule)).
- [ ] **Release note** — a `CHANGELOG.md` entry under *Unreleased* (Keep a
      Changelog format).
- [ ] **Build-note post** — a short build-in-public post (X thread / LinkedIn /
      blog) so the ship is visible outside the diff.

## Why

Shipping velocity only converts into momentum if each ship is *visible*. A
feature with no demo, no docs, and no post is invisible outside the diff. This
list is the minimum trail that turns a merge into a growth event.

Linked from [`CONTRIBUTING.md`](../CONTRIBUTING.md) and the
[release checklist](./release-checklist.md).

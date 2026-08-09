# Release checklist

Run this for every tagged release. It exists so a release is never "just a tag"
— it should ship with notes, a demo, upgrade guidance, and credit.

## Pre-release

- [ ] All PRs for the milestone merged; `dev` green on CI.
- [ ] `CHANGELOG.md` *Unreleased* section curated into a versioned section
      (Keep a Changelog format: Added / Changed / Fixed / Security).
- [ ] Version bumped where applicable (`GET /version`, package manifests).
- [ ] Migrations verified: `make migrate` (or `make lite-migrate`) applies
      cleanly from the previous release.

## Cut the release

- [ ] Tag `vX.Y.Z` and push.
- [ ] GitHub Release created from the tag with:
  - [ ] **Changelog** — the curated section for this version.
  - [ ] **Demo artifact** — GIF/screenshot of the headline feature.
  - [ ] **Upgrade notes** — env-var changes, new services, migration steps,
        any breaking changes and how to adapt.
  - [ ] **"What this unlocks"** — one paragraph on why this release matters to a
        user (not a diff summary).
  - [ ] **Contributor credits** — @-mention everyone who landed a PR.

## Post-release

- [ ] Build-in-public post (X thread / LinkedIn / blog build-note), linking the
      release.
- [ ] Close the milestone; move any spillover to the next.

## Dry run

The first real release (v0.1.0) should follow this list exactly as a dry run,
and any friction found should be folded back into this checklist.

See also the per-feature [ship checklist](./ship-checklist.md) and the
[backup & restore guide](./backup-restore.md) for upgrade safety.

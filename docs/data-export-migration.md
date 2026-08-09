# Data export & migration

OpenGrow hosted and self-hosted run the **same core schema** (Postgres) and the
**same object layout** (MinIO/S3-compatible), so moving between them is a
database dump plus an object-store copy — no proprietary export format, no
lock-in. This is a deliberate portability guarantee (see
[commercial options](../COMMERCIAL.md)).

## What holds your data

| Store | Contents |
|---|---|
| **Postgres** | Tenants, users, content pieces, generations + lineage, publications, analytics/attribution events, connectors, API keys |
| **Object storage** (MinIO / S3) | Uploaded asset **bytes** (brand/context files). Embeddings + snippets live on the Postgres row; in production the vector is mirrored to Qdrant and is rebuildable |

A Postgres dump + the asset objects is a complete, portable copy. See the
[backup & restore guide](./backup-restore.md) for the exact commands.

## Export: hosted → self-hosted

1. **Request/take a Postgres dump** of your tenant's database
   (`pg_dump`; hosted provides this on request or via a self-serve export).
2. **Copy asset objects** from the hosted bucket to yours
   (`mc mirror hosted/opengrow-assets local/opengrow-assets`).
3. **Stand up self-hosted** (`make lite-up` or `make prod-up`), then **restore**
   the dump and objects per the [restore steps](./backup-restore.md#restore-checklist).
4. **Reconcile config** — set your own `JWT_SECRET`, model keys (BYOK), and
   `GITHUB_TOKEN`. Run `make migrate` to align schema to your build.
5. **Verify** — log in, confirm content + publications load and an `INDEXED`
   asset still resolves.

## Import: self-hosted → hosted

1. Take a Postgres dump + asset objects from your instance
   ([backup guide](./backup-restore.md)).
2. Share them through the hosted onboarding (Team/Enterprise includes migration
   help — [commercial options](../COMMERCIAL.md)).
3. Hosted loads them into a fresh workspace DB (the hosted overlay uses a
   separate `opengrow_hosted` database over the same core schema) and mirrors
   objects into the managed bucket.
4. Re-enter secrets in the hosted vault (keys are never carried in exports;
   connector credentials are re-authorized).

## Versioned upgrades

- Migrations are Alembic-managed and forward-only; always run `make migrate`
  (or `make lite-migrate`) after moving data so the schema matches the target
  build.
- Restore Postgres and object storage from the **same point in time**
  (asset rows reference objects by key).
- Take a backup **before** every upgrade; keep the previous release's dump until
  the upgrade is verified.

## Guarantees

- **No proprietary format** — standard `pg_dump` + object files.
- **Both directions supported** — hosted ⇄ self-hosted.
- **Secrets never travel in data exports** — re-entered on the target.

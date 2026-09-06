# Data export & migration

Every OpenGrow deployment runs the **same core schema** (Postgres) and the
**same object layout** (MinIO/S3-compatible), so moving between instances is a
database dump plus an object-store copy — no proprietary export format, no
lock-in. This is a deliberate portability guarantee.

## What holds your data

| Store | Contents |
|---|---|
| **Postgres** | Tenants, users, content pieces, generations + lineage, publications, analytics/attribution events, connectors, API keys |
| **Object storage** (MinIO / S3) | Uploaded asset **bytes** (brand/context files). Embeddings + snippets live on the Postgres row; in production the vector is mirrored to Qdrant and is rebuildable |

A Postgres dump + the asset objects is a complete, portable copy. See the
[backup & restore guide](./backup-restore.md) for the exact commands.

## Moving between your own instances

1. **Take a Postgres dump + asset objects** from the source instance
   ([backup guide](./backup-restore.md)).
2. **Stand up the target** (`make lite-up` or `make prod-up`), then **restore**
   the dump and objects per the [restore steps](./backup-restore.md#restore-checklist).
3. **Reconcile config** — set your own `JWT_SECRET`, model keys (BYOK), and
   `GITHUB_TOKEN`. Run `make migrate` to align schema to the target build.
4. **Re-enter secrets on the target** (keys are never carried in exports;
   connector credentials are re-authorized).
5. **Verify** — log in, confirm content + publications load and an `INDEXED`
   asset still resolves.

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
- **Secrets never travel in data exports** — re-entered on the target.

# Backup & restore

OpenGrow keeps all durable state in **named Docker volumes** — Postgres
(relational data), MinIO (uploaded asset objects), and, in production, Qdrant
(vectors) plus OpenFGA / Infisical / Caddy. Backing up means snapshotting those
volumes; restoring means loading them back into a stopped stack.

## Production stack — `make backup` / `make restore`

The bundled scripts target the **base/production** compose volumes.

```bash
make backup                 # → ./backups/<YYYY-MM-DD-HHMM>/<volume>.tar.gz
make restore ts=2026-08-06-1130
```

`infra/scripts/backup.sh` tars each of these volumes (prefixed `opengrow_`) into
a timestamped folder, skipping any that aren't present:

```
postgres_data  redis_data  qdrant_data  minio_data  openfga_data
infisical_data  caddy_data
```

Each is captured with a throwaway `alpine` container:

```bash
docker run --rm -v opengrow_postgres_data:/data -v "$OUT":/backup alpine \
  tar -czf /backup/postgres_data.tar.gz -C /data .
```

`make restore ts=<timestamp>` reverses it from `./backups/<timestamp>/`.

**Recommended:** stop app services before backup/restore for a consistent
snapshot (`make down` / `make restore …` while stopped), or take a logical
Postgres dump (below) if you need a hot backup.

## Lite stack

The lite stack uses **different volume names** (`*_data_lite`), so `make backup`
(which looks for `opengrow_postgres_data`, etc.) will report them as "not
present." Back lite volumes up directly:

```bash
mkdir -p backups/lite-$(date -u +%Y-%m-%d-%H%M)
OUT=backups/lite-$(date -u +%Y-%m-%d-%H%M)
for v in postgres_data_lite minio_data_lite redis_data_lite; do
  docker run --rm -v "opengrow_${v}":/data -v "$PWD/$OUT":/backup alpine \
    tar -czf "/backup/${v}.tar.gz" -C /data .
done
```

Restore into a **stopped** lite stack (`make lite-down`), then for each volume:

```bash
docker run --rm -v opengrow_postgres_data_lite:/data -v "$PWD/$OUT":/backup alpine \
  sh -c "rm -rf /data/* && tar -xzf /backup/postgres_data_lite.tar.gz -C /data"
make lite-up
```

> `redis_data_lite` is a broker/cache and is optional to back up.
> `ollama_data_lite` holds downloaded models — large and re-pullable, so skip it
> unless you want to avoid re-downloading.

## Logical Postgres backup (portable, hot)

For a database-only, engine-portable backup you can take while running:

```bash
# lite
docker compose -f docker-compose.lite.yml exec -T postgres \
  pg_dump -U opengrow opengrow | gzip > opengrow-$(date -u +%F).sql.gz

# restore
gunzip -c opengrow-YYYY-MM-DD.sql.gz | \
  docker compose -f docker-compose.lite.yml exec -T postgres psql -U opengrow -d opengrow
```

## Object storage (MinIO) considerations

- Uploaded asset **bytes** live only in the MinIO volume (`minio_data*`).
  Postgres holds the metadata and the embedding vector, **not** the original
  file — so a Postgres-only backup does **not** capture uploaded assets. Back up
  the MinIO volume too, or mirror the buckets with `mc mirror` to external
  storage.
- Keep the Postgres and MinIO snapshots from the **same point in time** so asset
  rows and their objects stay consistent.
- Store backups off-host; the `./backups/` folder is local to the machine.

## Restore checklist

1. Stop app services (`make down` / `make lite-down`).
2. Restore Postgres **and** MinIO from the **same** backup timestamp.
3. Start the stack; run `make migrate` / `make lite-migrate` (a no-op if the
   backup already matched schema).
4. Log in and confirm content + assets load and an `INDEXED` asset still
   resolves.

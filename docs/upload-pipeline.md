# Asset upload pipeline

How an uploaded asset moves from raw bytes to retrievable grounding context, for
operators and security reviewers. The status enum lives in
[`app/models/asset.py`](../services/fastapi-core/app/models/asset.py); the async
work is in [`app/workers/tasks.py`](../services/fastapi-core/app/workers/tasks.py).

## Lifecycle

```
POST /assets/upload
      │  (bytes → MinIO TEMP bucket, row created)
      ▼
  UPLOADED ──► SCANNING ──► SCANNED ──► EMBEDDING ──► INDEXED
                  │             │            │
                  ▼             ▼            ▼
             SCAN_FAILED   SCAN_FAILED   EMBED_FAILED
             (infected/    (promote to
              fetch error)  assets bucket
                            failed)
```

| Status | Meaning |
|---|---|
| `UPLOADED` | Bytes are in the **temp** bucket, row created, scan queued |
| `SCANNING` | ClamAV scan in progress (`scan_asset` task) |
| `SCAN_FAILED` | ClamAV `FOUND`/`ERROR`, temp fetch failed, or promotion failed — file never enters the assets bucket |
| `SCANNED` | Clean; object **promoted** from the temp bucket to the **assets** bucket; embedding queued |
| `EMBEDDING` | Computing the embedding vector (`embed_asset` task) |
| `EMBED_FAILED` | Embedding call raised; retried up to 3× before this state sticks |
| `INDEXED` | Vector + text snippet persisted; the asset is now usable as generation grounding |

Failure states carry a human-readable reason in `asset.scan_message`.

## Stages in detail

1. **Upload** — `POST /assets/upload` streams the file into the MinIO **temp**
   bucket (`MINIO_BUCKET_TEMP`), creates the `Asset` row as `UPLOADED`, and
   enqueues `scan_asset`.
2. **Scan** (`scan_asset`, Celery) — sets `SCANNING`, fetches the bytes, and
   calls `scan_bytes()`:
   - **Production:** streams the bytes to ClamAV. Not clean → `SCAN_FAILED`, and
     the file stays quarantined in the temp bucket.
   - **Lite:** `scan_bytes()` returns `skipped-lite-mode` — no ClamAV, uploads
     are trusted (see [threat-model.md](./threat-model.md)).
   - On clean, the object is **promoted** to the assets bucket
     (`MINIO_BUCKET_ASSETS`), `object_key` is set, status → `SCANNED`, and
     `embed_asset` is enqueued.
3. **Embed + index** (`embed_asset`, Celery) — only runs for a `SCANNED` asset.
   Sets `EMBEDDING`, then:
   - Text assets (`content_type` starts with `text/`) are decoded (first ~20k
     chars); binary assets use `filename + content-type` as a proxy string.
   - LiteLLM computes the embedding vector; the vector and a short
     `text_snippet` are stored **on the Asset row** (both modes).
   - **Production** additionally upserts the vector into **Qdrant**; **lite**
     ranks from Postgres only.
   - Status → `INDEXED`. On any exception → `EMBED_FAILED`.

## Lite vs production differences

| | Lite | Production |
|---|---|---|
| Malware scan | Skipped (`skipped-lite-mode`) | ClamAV on every upload |
| Vector store | Postgres row only | Qdrant + Postgres |
| Retrieval ranking | In-Postgres | Qdrant ANN |

## Operational notes

- Generation grounding uses only `INDEXED` assets. Poll `GET /assets/{id}` until
  `status == "INDEXED"` before expecting an asset to influence a generation.
- A stuck `SCANNING`/`EMBEDDING` usually means the Celery worker is down — check
  `docker compose -f docker-compose.lite.yml logs celery-worker`.
- `EMBED_FAILED` in lite most often means the embedding model isn't available
  (e.g. `ollama pull nomic-embed-text` not run).

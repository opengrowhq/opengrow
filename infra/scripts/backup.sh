#!/usr/bin/env bash
# Backup all named docker volumes → ./backups/YYYY-MM-DD-HHMM/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TS=$(date -u +%Y-%m-%d-%H%M)
OUT="$ROOT/backups/$TS"
mkdir -p "$OUT"

echo "== Backup → $OUT =="

VOLUMES=(
	postgres_data
	redis_data
	qdrant_data
	minio_data
	openfga_data
	infisical_data
	caddy_data
)

for vol in "${VOLUMES[@]}"; do
	full="opengrow_${vol}"
	if docker volume inspect "$full" >/dev/null 2>&1; then
		echo "  ${full} → ${vol}.tar.gz"
		docker run --rm -v "$full":/data -v "$OUT":/backup alpine \
			tar -czf "/backup/${vol}.tar.gz" -C /data .
	else
		echo "  skip ${full} (not present)"
	fi
done

echo "Backup complete: $OUT"

#!/usr/bin/env bash
# Restore from ./backups/<timestamp>/ → replace all named volumes.
set -euo pipefail

if [ $# -lt 1 ]; then
	echo "Usage: $0 <timestamp-dir under ./backups/>"
	exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IN="$ROOT/backups/$1"
if [ ! -d "$IN" ]; then
	echo "Not a directory: $IN"
	exit 1
fi

echo "== Restore from $IN =="
echo "This will REPLACE all matching docker volumes. Ctrl-C in 5s to abort."
sleep 5

cd "$ROOT"
docker compose down

for archive in "$IN"/*.tar.gz; do
	base=$(basename "$archive" .tar.gz)
	full="opengrow_${base}"
	echo "  ${full}"
	docker volume rm "$full" >/dev/null 2>&1 || true
	docker volume create "$full" >/dev/null
	docker run --rm -v "$full":/data -v "$IN":/backup alpine \
		sh -c "cd /data && tar -xzf /backup/${base}.tar.gz"
done

echo "Restore complete. Run: make up-d"

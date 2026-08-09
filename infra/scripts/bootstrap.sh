#!/usr/bin/env bash
# One-shot local bootstrap: generate secrets, write to ./infra/secrets/*, seed Infisical, run migrations.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SEC_DIR="$ROOT/infra/secrets"
mkdir -p "$SEC_DIR"

gen() { openssl rand -hex 32; }

write_if_missing() {
	local file="$1" value="$2"
	if [ ! -s "$file" ]; then
		printf '%s' "$value" > "$file"
		echo "  wrote $file"
	else
		echo "  kept  $file (existing)"
	fi
}

echo "== 1) Generating dev secrets (idempotent) =="
write_if_missing "$SEC_DIR/pg_password"                "$(gen)"
write_if_missing "$SEC_DIR/minio_root_user"            "opengrow"
write_if_missing "$SEC_DIR/minio_root_password"        "$(gen)"
PG_PW=$(cat "$SEC_DIR/pg_password")
OPENFGA_URI="postgres://opengrow:$PG_PW@postgres:5432/opengrow?sslmode=disable"
write_if_missing "$SEC_DIR/openfga_datastore_uri"      "$OPENFGA_URI"
write_if_missing "$SEC_DIR/infisical_encryption_key"   "$(openssl rand -hex 16)"
write_if_missing "$SEC_DIR/infisical_auth_secret"      "$(gen)"
write_if_missing "$SEC_DIR/infisical_db_uri"           "$OPENFGA_URI"
write_if_missing "$SEC_DIR/litellm_master_key"         "sk-$(gen)"
write_if_missing "$SEC_DIR/litellm_db_uri"             "$OPENFGA_URI"

echo
echo "== 2) Ensuring .env exists =="
if [ ! -f "$ROOT/.env" ]; then
	cp "$ROOT/.env.example" "$ROOT/.env"
	echo "  copied .env.example -> .env"
	echo "  NOTE: set INFISICAL_TOKEN in .env after Infisical is up."
fi

echo
echo "== 3) Starting infra dependencies =="
cd "$ROOT"
docker compose up -d postgres redis qdrant minio clamav

echo
echo "== 4) Waiting for postgres ready =="
until docker compose exec -T postgres pg_isready -U opengrow -d opengrow >/dev/null 2>&1; do
	sleep 2
done
echo "  postgres ready"

echo
echo "== 5) Starting OpenFGA + Infisical + LiteLLM =="
docker compose up -d openfga infisical litellm
sleep 5

cat <<EOF

==================================================================
Bootstrap complete.

Next manual steps:
  1) Open Infisical UI:  http://127.0.0.1:8090
     - create project id: opengrow-dev
     - create environment: dev
     - add secrets: POSTGRES_PASSWORD, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
       OPENFGA_STORE_ID, OPENFGA_MODEL_ID, LITELLM_MASTER_KEY,
       JWT_SECRET, OPENAI_API_KEY (or leave blank for Ollama-only)
     - generate a machine identity token, paste into .env as INFISICAL_TOKEN

  2) Open OpenFGA playground: http://127.0.0.1:3000
     - paste infra/openfga/model.fga
     - copy STORE_ID + MODEL_ID back into Infisical

  3) make up-d
  4) make migrate
  5) make seed
  6) make test-e2e
==================================================================
EOF

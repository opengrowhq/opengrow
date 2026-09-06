SHELL := bash
.DEFAULT_GOAL := help
COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml

.PHONY: help bootstrap up up-d down restart logs ps migrate seed seed-demo test test-e2e scan lint format shell db-shell backup restore prod-up prod-down prod-logs lite-up lite-down lite-migrate lite-seed lite-logs lite-shell lite-nuke

COMPOSE_LITE := docker compose -f docker-compose.lite.yml

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## One-time: generate secrets, seed Infisical, run migrations
	@bash infra/scripts/bootstrap.sh

up: ## Start dev stack (foreground)
	$(COMPOSE) up

up-d: ## Start dev stack (background)
	$(COMPOSE) up -d
	@$(MAKE) --no-print-directory logs-tail

logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100

logs-tail:
	@echo "== Services =="
	@$(COMPOSE) ps

down: ## Stop dev stack (keep volumes)
	$(COMPOSE) down

nuke: ## Stop + remove volumes (destructive)
	$(COMPOSE) down -v

restart: ## Restart all app services
	$(COMPOSE) restart fastapi-core celery-worker-light celery-worker-heavy celery-beat node-gateway

ps: ## Show service status
	$(COMPOSE) ps

migrate: ## Run Alembic migrations (Python side)
	$(COMPOSE) exec fastapi-core alembic upgrade head

migration: ## Generate Alembic migration: make migration m="add foo table"
	$(COMPOSE) exec fastapi-core alembic revision --autogenerate -m "$(m)"

seed: ## Seed one demo tenant + demo user + OpenFGA relations
	$(COMPOSE) exec fastapi-core python -m scripts.seed

seed-demo: ## Load examples/ fixtures into a RUNNING instance (brand, content, attribution). Override GW=... (default :8000)
	@bash infra/scripts/seed-demo.sh

test: ## Run backend + gateway tests
	$(COMPOSE) exec fastapi-core pytest -x --tb=short
	$(COMPOSE) exec node-gateway npm test

test-e2e: ## Run the vertical-slice E2E script (curl-based)
	@bash tests/e2e/vertical_slice.sh

scan: ## Trigger a ClamAV signature refresh
	$(COMPOSE) exec clamav freshclam

lint: ## Lint backend (ruff) + gateway (eslint)
	$(COMPOSE) exec fastapi-core ruff check .
	$(COMPOSE) exec node-gateway npm run lint

format: ## Format backend + gateway
	$(COMPOSE) exec fastapi-core ruff format .
	$(COMPOSE) exec node-gateway npm run format

shell: ## Shell into FastAPI container
	$(COMPOSE) exec fastapi-core bash

db-shell: ## Postgres psql shell
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-opengrow} -d $${POSTGRES_DB:-opengrow}

backup: ## Backup all named volumes to ./backups/
	@bash infra/scripts/backup.sh

restore: ## Restore from ./backups/<timestamp>/
	@bash infra/scripts/restore.sh $(ts)

prod-up: ## Prod bring-up (Debian)
	$(COMPOSE_PROD) up -d

prod-down: ## Prod stop
	$(COMPOSE_PROD) down

prod-logs: ## Prod logs
	$(COMPOSE_PROD) logs -f --tail=200

# ---- Lite mode (personal / single-tenant, 8 services) ----
lite-up: ## Start lite stack (personal use, 8 services)
	@[ -f .env ] || (echo "  → seeding .env from .env.lite.example"; cp .env.lite.example .env)
	$(COMPOSE_LITE) up -d
	@echo "  → run: make lite-migrate && make lite-seed"

lite-down: ## Stop lite stack (keep data)
	$(COMPOSE_LITE) down

lite-nuke: ## Stop + remove lite data (destructive)
	$(COMPOSE_LITE) down -v

lite-migrate: ## Apply migrations in lite mode
	$(COMPOSE_LITE) exec fastapi-core alembic upgrade head

lite-seed: ## Seed demo tenant + user in lite mode
	$(COMPOSE_LITE) exec fastapi-core python -m scripts.seed

lite-logs: ## Follow lite logs
	$(COMPOSE_LITE) logs -f --tail=100

lite-shell: ## Bash into fastapi-core (lite)
	$(COMPOSE_LITE) exec fastapi-core bash

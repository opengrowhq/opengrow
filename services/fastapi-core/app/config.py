from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.secrets import fetch_secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # ---- Runtime identity ----
    SERVICE_NAME: str = "fastapi-core"
    OPENGROW_ENV: str = "dev"
    HOSTED_MODE: bool = False

    # ---- CORS ----
    # Comma-separated browser origins allowed to call the API directly (lite
    # mode: the browser hits fastapi-core; production goes via the BFF).
    # Empty → sensible localhost dev default (see `cors_origins`).
    CORS_ORIGINS: str = ""

    # ---- Deployment mode ----
    # "production" — full 15-service stack (Infisical, OpenFGA, ClamAV, LiteLLM proxy, etc)
    # "lite"       — 5-service personal-use stack (env-var secrets, stub authz, no ClamAV, in-process LiteLLM)
    DEPLOYMENT_MODE: Literal["production", "lite"] = "production"

    # "proxy"   — LiteLLM runs as separate container; we call it via HTTP
    # "library" — LiteLLM imported as Python package; we call it in-process (lite mode default)
    LITELLM_MODE: Literal["proxy", "library"] = "proxy"

    # ---- Infisical (production only) ----
    INFISICAL_URL: str = ""
    INFISICAL_PROJECT_ID: str = ""
    INFISICAL_ENVIRONMENT: str = "dev"
    INFISICAL_TOKEN: str = ""

    # ---- Infra hostnames (non-secret) ----
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_BROKER_DB: int = 0
    REDIS_RESULT_DB: int = 1
    REDIS_CACHE_DB: int = 2
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    MINIO_HOST: str
    MINIO_PORT: int = 9000
    MINIO_BUCKET_ASSETS: str = "opengrow-assets"
    MINIO_BUCKET_TEMP: str = "opengrow-temp"
    CLAMAV_HOST: str = "clamav"
    CLAMAV_PORT: int = 3310
    OPENFGA_API_URL: str = "http://openfga:8080"
    LITELLM_URL: str = "http://litellm:4000"
    MAILPIT_HOST: str = "mailpit"
    MAILPIT_SMTP_PORT: int = 1025

    # ---- Secrets ----
    # Production: fetched from Infisical at import.
    # Lite:       read straight from env vars (docker-compose.lite.yml injects them).
    POSTGRES_PASSWORD: str = ""
    REDIS_PASSWORD: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    OPENFGA_STORE_ID: str = ""
    OPENFGA_MODEL_ID: str = ""
    LITELLM_MASTER_KEY: str = ""
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_MINUTES: int = 30
    JWT_REFRESH_DAYS: int = 30

    # ---- Rate limiting (per-tenant/token, Redis fixed-window) ----
    # Off by default so lite/self-host is unthrottled; hosted enables it.
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 120

    # ---- BYOK LLM keys (lite mode: read directly by LiteLLM library) ----
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    # Model used for generation + Brand DNA when a request doesn't specify one.
    # Must be LiteLLM-resolvable — bare OpenAI names work, other providers
    # need their prefix (LiteLLM can't route/price the call otherwise):
    # e.g. "gpt-5-mini" (OpenAI), "claude-sonnet-4-5" (Anthropic),
    # "gemini/gemini-flash-latest" (Google), or "llama3.1" (local Ollama, free).
    DEFAULT_LLM_MODEL: str = "gpt-5-mini"
    # Embedding model passed to LiteLLM. Defaults to a free local Ollama model
    # in lite mode (no OpenAI key required) and OpenAI's small embedding model
    # in production. Override via env var if you have a different Ollama
    # model pulled (e.g. `ollama pull nomic-embed-text`).
    EMBEDDING_MODEL: str = ""

    # ---- BYOK publishing (GitHub PR publishing) ----
    GITHUB_TOKEN: str = ""
    GITHUB_API_URL: str = "https://api.github.com"

    # ---- Google analytics/search connector OAuth (optional) ----
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = ""

    # ---- Stripe billing (hosted only — Pro/Team paid tiers, managed LLM key) ----
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_PRO: str = ""
    STRIPE_PRICE_ID_TEAM: str = ""
    # Team plan is base + per-seat: STRIPE_PRICE_ID_TEAM covers the first
    # TEAM_INCLUDED_SEATS members; this price bills each seat beyond that,
    # as a second line item on the same subscription (not a separate one).
    STRIPE_PRICE_ID_TEAM_SEAT: str = ""
    TEAM_INCLUDED_SEATS: int = 5
    # Base URL the browser is served from — Checkout/Billing Portal redirect here.
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # ---- Orchestrator article-pipeline quality gate ----
    # A draft below this score (0.0-1.0, see app/core/quality_score.py) is
    # regenerated with feedback instead of promoted, up to ARTICLE_SCORE_MAX_RETRIES
    # times. v1 scores on-page signals only (keyword/heading coverage, length,
    # readability) — no external SERP comparison (would need a paid search API).
    ARTICLE_SCORE_THRESHOLD: float = 0.6
    ARTICLE_SCORE_MAX_RETRIES: int = 2

    @property
    def is_lite(self) -> bool:
        return self.DEPLOYMENT_MODE == "lite"

    @property
    def embedding_model(self) -> str:
        if self.EMBEDDING_MODEL:
            return self.EMBEDDING_MODEL
        return "ollama/nomic-embed-text" if self.is_lite else "text-embedding-3-small"

    @property
    def cors_origins(self) -> list[str]:
        if self.CORS_ORIGINS:
            return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_sync_dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_broker_url(self) -> str:
        pw = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{pw}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_BROKER_DB}"

    @property
    def redis_result_url(self) -> str:
        pw = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{pw}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_RESULT_DB}"

    @property
    def redis_cache_url(self) -> str:
        pw = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{pw}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_CACHE_DB}"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.DEPLOYMENT_MODE == "production":
        remote = fetch_secrets(
            url=s.INFISICAL_URL,
            project_id=s.INFISICAL_PROJECT_ID,
            environment=s.INFISICAL_ENVIRONMENT,
            token=s.INFISICAL_TOKEN,
        )
        for key, value in remote.items():
            if hasattr(s, key) and value:
                setattr(s, key, value)
    # Lite mode: everything already in env vars via docker-compose.lite.yml → pydantic-settings picks them up.
    return s


settings = get_settings()

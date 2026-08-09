"""Unit tests for EMBEDDING_MODEL resolution (lite default vs hosted default)."""

from app.config import Settings

_REQUIRED = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_DB": "opengrow",
    "POSTGRES_USER": "opengrow",
    "REDIS_HOST": "localhost",
    "MINIO_HOST": "localhost",
}


def _settings(**overrides):
    return Settings(**(_REQUIRED | overrides))


def test_lite_defaults_to_local_ollama_embedding():
    s = _settings(DEPLOYMENT_MODE="lite")
    assert s.embedding_model == "ollama/nomic-embed-text"


def test_production_defaults_to_openai_embedding():
    s = _settings(DEPLOYMENT_MODE="production")
    assert s.embedding_model == "text-embedding-3-small"


def test_explicit_override_wins_in_lite():
    s = _settings(DEPLOYMENT_MODE="lite", EMBEDDING_MODEL="text-embedding-3-small")
    assert s.embedding_model == "text-embedding-3-small"

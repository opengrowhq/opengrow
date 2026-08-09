"""LiteLLM gateway client — the ONLY path to model providers.

Production (LITELLM_MODE=proxy): HTTP calls to the LiteLLM container.
Lite     (LITELLM_MODE=library): direct calls to the `litellm` Python package.

Both paths honor the invariant that no `openai`/`anthropic`/`google-generativeai`
import ever appears in application code.
"""

from __future__ import annotations
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

log = logging.getLogger("litellm")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.LITELLM_MASTER_KEY}",
        "Content-Type": "application/json",
    }


def _library_env() -> None:
    """Populate env vars that `litellm` reads at call time."""
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    if settings.ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
    if settings.GOOGLE_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GOOGLE_API_KEY
    if settings.OLLAMA_BASE_URL:
        os.environ["OLLAMA_API_BASE"] = settings.OLLAMA_BASE_URL


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def embed(text: str, model: str | None = None) -> list[float]:
    model = model or settings.embedding_model
    if settings.LITELLM_MODE == "library":
        _library_env()
        from litellm import aembedding  # imported here to keep import surface tight

        resp = await aembedding(model=model, input=text)
        return resp["data"][0]["embedding"]

    # proxy mode
    import httpx

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.LITELLM_URL}/embeddings",
            json={"model": model, "input": text},
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def chat_completion(
    messages: list[dict],
    model: str = "gpt-4o-mini",
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> str:
    if settings.LITELLM_MODE == "library":
        _library_env()
        from litellm import acompletion

        resp = await acompletion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp["choices"][0]["message"]["content"]

    # proxy mode
    import httpx

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{settings.LITELLM_URL}/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

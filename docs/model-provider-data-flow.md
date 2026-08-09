# Model-provider data flow

OpenGrow is **bring-your-own-key (BYOK)** and provider-agnostic. Every model
call — generations, the orchestrator, and embeddings — routes through **LiteLLM**,
so the provider that sees your data is whichever one the selected model maps to.
This doc states exactly what leaves your machine, and when.

## The path

```
app code ──► LiteLLM ──► provider
  (generation / orchestrator / embedding)      ├─ ollama/*   → local Ollama (in-stack, nothing leaves the host)
                                               ├─ openai/*   → OpenAI API      (needs OPENAI_API_KEY)
                                               ├─ anthropic/* → Anthropic API  (needs ANTHROPIC_API_KEY)
                                               └─ gemini/*   → Google API      (needs GOOGLE_API_KEY)
```

- In **lite**, LiteLLM runs **in-process** (`LITELLM_MODE=library`) — there is no
  separate proxy. In **production** it runs as the LiteLLM proxy service. The
  routing rules and this data-flow are identical either way.
- The model is chosen per request (e.g. `"model": "ollama/llama3.1"`), falling
  back to `DEFAULT_LLM_MODEL` (lite default: `ollama/llama3.1`).
- Embeddings use `EMBEDDING_MODEL`; when unset in lite it defaults to
  `ollama/nomic-embed-text` — i.e. **embeddings are computed locally by default.**

## What is sent to a third-party provider

When you select an **external** model (`openai/*`, `anthropic/*`, `gemini/*`),
the request LiteLLM sends to that provider includes:

- your **brief / prompt**,
- **brand context** and any **retrieved asset snippets** used as grounding,
- generation parameters.

That data is transmitted to, and processed by, the chosen provider under **your**
API key and that provider's data-handling terms. OpenGrow does not add a
middle-man service — keys are yours, calls go directly to the provider.

## What stays local

- With an **`ollama/*`** model, generation runs against the in-stack Ollama
  container over `OLLAMA_BASE_URL` (default `http://ollama:11434`). **No prompt,
  content, or asset text leaves the host.**
- With the default lite embedding model (`ollama/nomic-embed-text`), **embedding
  also stays local**, even if you use an external provider for generation.
- Uploaded asset **bytes** live in your MinIO bucket; only the derived **text
  snippet** used as grounding is sent to the generation provider (and only when
  that provider is external).

## Choosing your privacy posture

| Goal | Configuration |
|---|---|
| Nothing leaves the host | `DEFAULT_LLM_MODEL=ollama/…` **and** `EMBEDDING_MODEL` unset/`ollama/…` |
| Best quality, external OK | `DEFAULT_LLM_MODEL=openai/… \| anthropic/… \| gemini/…` + that provider's key |
| External generation, local embeddings | external `DEFAULT_LLM_MODEL` + leave `EMBEDDING_MODEL` on the Ollama default |

No API key is required for the Ollama path. Keys are only read when a request
actually targets that provider.

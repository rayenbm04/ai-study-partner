# LLM & Embedding Providers — Cloud-First, With a Card-Free Local Fallback

Decision: cloud APIs by default (no Ollama, no on-disk weights) for chat/vision, starting
on free tiers, with a paid upgrade path that requires no code changes — only a model-name
change, because `services/llm/` and `services/embeddings/` sit behind a provider interface.

**Update, late 2026**: Google started requiring a billing account on file for Gemini's free
tier (the tier itself still doesn't charge, but the account must have a card attached) —
a dealbreaker for anyone who can't/won't add one. `EMBEDDING_PROVIDER=local` runs an
open-source `sentence-transformers` model (`all-mpnet-base-v2`, 768-dim — matches
`EMBEDDING_DIMENSION` exactly, no migration needed) on the backend's own CPU instead: no
key, no card, no network call once the model is cached after first use. Pair it with
`LLM_PROVIDER=groq` for chat (Groq's free tier has never required a card) to run the whole
pipeline without any billing account anywhere. See `app/services/embeddings/local_embedder.py`.

**Update, later in 2026**: added **Cerebras** as a second cloud-chat option, usable either
standalone (`LLM_PROVIDER=cerebras`) or paired with Groq via `LLM_FALLBACK_PROVIDER=groq`
(see "Multi-provider strategy: Cerebras + Groq" below). Cerebras' free tier is unusually
generous for a text-only provider — no card required — but it currently has no
vision-capable model, unlike Groq's separate vision lineup or Gemini/OpenAI's native
multimodal chat models; pair it with a fallback if this app needs to read scanned PDFs or
image uploads.

## Recommendation

| Role | Provider | Why |
|---|---|---|
| Default chat + vision (tutoring, summaries, concept tagging, quiz/exam generation, image/slide extraction) | **Google Gemini** (`gemini-2.5-flash`) | Free tier: ~1,500 requests/day, no credit card, no expiry. Natively multimodal, so it replaces the local vision model the fork used for scanned pages and diagrams — one provider instead of a separate vision pipeline. |
| Default embeddings | **Google Gemini Embedding** (`gemini-embedding-001`), or **local `sentence-transformers`** (`EMBEDDING_PROVIDER=local`) if you don't want a billing account on file | Gemini: 1,500 requests/day, 10M tokens/min, same account as chat. Local: genuinely free forever, no key, no card, runs on the backend's own CPU — see the update note above. |
| Card-free chat alternative, primary in a Cerebras + Groq pairing | **Cerebras** (`gpt-oss-120b`, aux tier `llama3.1-8b`) | Free tier: 30 requests/minute, 14.4K requests/day, 1M tokens/day on GPT-OSS-120B, with similarly generous limits on its 8B model — no credit card. See "Multi-provider strategy" below for why this is worth pairing with Groq rather than using alone. |
| High-volume / bulk generation fallback (flashcard batches, quiz batches, retry queue when Gemini's or Cerebras' daily quota is hit) | **Groq** (`llama-3.3-70b-versatile`) | Free tier, no credit card, and the fastest inference available at any price — 700+ tokens/sec on custom LPU hardware. Good enough quality for flashcard Q&A and MCQ generation where speed matters more than frontier reasoning. Also the natural `LLM_FALLBACK_PROVIDER` for Cerebras, since it's the one provider here with a genuinely separate vision-capable model. |
| Aggregation layer + the paid upgrade path | **OpenRouter** | One API key routes to 28+ models, including a free pool (DeepSeek R1, Llama 3.3 70B, Qwen3, Gemma 3, Gemini Flash) for overflow/failover, and the exact same integration reaches paid Claude or GPT-4o the moment budget allows — just change `OPENROUTER_CHAT_MODEL` in `.env`, nothing else. |

`config.py` already has all five sets of keys/model names scaffolded (`GEMINI_*`,
`GROQ_*`, `CEREBRAS_*`, `OPENROUTER_*`, plus unused `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` for
direct paid access later). `LLM_PROVIDER` and `EMBEDDING_PROVIDER` pick which one is active;
switching providers is a `.env` change, not a code change, since `services/llm/` and
`services/embeddings/` sit behind a provider interface.

## Why this combination and not a single provider

Free tiers are rate-limited (Gemini: 10–15 requests/minute; Groq: ~30 requests/minute;
Cerebras: ~30 requests/minute), which a single busy student session (chat + background
flashcard/quiz generation) can hit. Splitting "interactive chat" (Gemini, or Cerebras) from
"bulk background generation" (Groq) keeps the student-facing chat responsive even when a big
quiz batch is being generated, and OpenRouter's free pool is the shock absorber if either
primary is temporarily throttled. All of these are reachable through the same `LLMProvider`
interface, so this is a routing decision inside `services/llm/factory.py`, not a different
integration per provider.

## Multi-provider strategy: Cerebras + Groq

The fix for "every free tier has a ceiling" isn't finding one provider with no limits — there
isn't one — it's combining two so a ceiling on one doesn't stall the app. Cerebras is the
interesting one to add on top of the Gemini/Groq pairing above: its free tier currently lists
**GPT-OSS-120B** at 30 requests/minute, 14.4K requests/day, and 1M tokens/day, with similarly
generous limits on its 8B model — enough headroom that it can be the *primary* chat provider,
with Groq as the fallback rather than the other way around.

```
User
  │
  ▼
Backend (FastAPI)
  │
  ▼
Check user's daily quota  ← UsageService, independent of whichever
  │                          provider ends up serving the call
  ▼
RAG retrieval              ← unchanged, see backend/README.md
  │
  ▼
AI Gateway (services/llm/factory.py)
  ├── Cerebras   (primary  — gpt-oss-120b / llama3.1-8b aux)
  └── Groq       (fallback — on a 429 or an exhausted daily quota)
```

**Task routing**, once `LLM_PROVIDER=cerebras` + `LLM_FALLBACK_PROVIDER=groq` are set:

| Task | Model |
|---|---|
| Tutoring / chat answers (reasoning-heavy) | Cerebras `gpt-oss-120b` |
| Concept tagging, classification, summaries, flashcard/quiz generation, RAG query rewriting | Cerebras `llama3.1-8b` (the same main/simple split every provider uses, see `llm/factory.py`) |
| Any vision call (scanned PDF pages, standalone images) | Routed straight to Groq — Cerebras has no vision-capable model at all, see `fallback_provider.py` |
| Whenever Cerebras returns a 429 or its daily quota is exhausted | Groq (`llama-3.3-70b-versatile` for answers, `llama-3.1-8b-instant` for aux) |

This is implemented as `FallbackLLMProvider` (`app/services/llm/fallback_provider.py`), built by
`build_llm_provider`/`build_simple_llm_provider` whenever `LLM_FALLBACK_PROVIDER` is set to
something other than `LLM_PROVIDER` itself — unset (the default) means no wrapping at all, same
single-provider behavior as before this existed. The per-user quota check (`UsageService`, see
`backend/README.md`'s Usage tracking section) happens in the backend's own code, ahead of both
RAG retrieval and the AI Gateway — it's a budget on *your* users, separate from (and enforced
before you ever hit) whatever rate limit either provider imposes on you.

> Exact Cerebras model IDs and limits move — check
> [inference.cerebras.ai/docs](https://inference.cerebras.ai/docs) before relying on
> `CEREBRAS_CHAT_MODEL` / `CEREBRAS_SIMPLE_CHAT_MODEL`'s defaults for capacity planning.

## Rate limits, current as of this writing (verify before relying on them for capacity planning — free-tier limits change often)

- Gemini API: ~10–15 requests/minute, ~1,500 requests/day on Flash, no credit card, up to 1M token context.
- Groq: ~30 requests/minute free on Llama 3.3 70B, no credit card.
- Cerebras: 30 requests/minute, 14.4K requests/day, 1M tokens/day on GPT-OSS-120B, no credit card; similarly generous limits on its 8B model.
- OpenRouter free tier: 20 requests/minute, 50–1,000 requests/day across 28+ free models, no credit card.
- Gemini Embedding: ~1,500 requests/day, 10M tokens/minute, no credit card.

Sources:
- [Free LLM API in 2026: 13 Options Ranked and Compared — OpenRouter Blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/)
- [Best Free LLM APIs in 2026 — Compare Free Inference Tiers, Rate Limits & Models](https://agentdeals.dev/free-llm-apis)
- [OpenRouter Free Tier 2026: Rate Limits, Models, BYOK](https://klymentiev.com/blog/openrouter-free-tier)
- [Best Free LLM API Tiers in 2026: Groq, Cerebras, GitHub Models & More](https://wetheflywheel.com/en/ai-model-access/free-llm-api-tiers-2026/)
- [Best Free Embedding Models & APIs in 2026](https://www.edenai.co/post/top-free-embedding-tools-apis-and-open-source-models)
- [Text Embedding Models 2026: Google vs OpenAI vs Voyage](https://tokenmix.ai/blog/text-embedding-models-comparison)
- [Cerebras Inference docs](https://inference.cerebras.ai/docs) — current models, rate limits, and pricing

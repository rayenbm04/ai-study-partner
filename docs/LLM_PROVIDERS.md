# LLM & Embedding Providers — Cloud-Only, Free-Tier-First

Decision: no local inference anywhere in the pipeline (no Ollama, no on-disk weights).
Every chat, extraction/vision, and embedding call goes to a cloud API, starting on free
tiers, with a paid upgrade path that requires no code changes — only a model-name change,
because `services/llm/` and `services/embeddings/` sit behind a provider interface.

## Recommendation

| Role | Provider | Why |
|---|---|---|
| Default chat + vision (tutoring, summaries, concept tagging, quiz/exam generation, image/slide extraction) | **Google Gemini** (`gemini-2.5-flash`) | Free tier: ~1,500 requests/day, no credit card, no expiry. Natively multimodal, so it replaces the local vision model the fork used for scanned pages and diagrams — one provider instead of a separate vision pipeline. |
| Default embeddings | **Google Gemini Embedding** (`gemini-embedding-001`) | Free tier: 1,500 requests/day, 10M tokens/min — same account as chat, one API key, no separate embedding vendor to manage. |
| High-volume / bulk generation fallback (flashcard batches, quiz batches, retry queue when Gemini's daily quota is hit) | **Groq** (`llama-3.3-70b-versatile`) | Free tier, no credit card, and the fastest inference available at any price — 700+ tokens/sec on custom LPU hardware. Good enough quality for flashcard Q&A and MCQ generation where speed matters more than frontier reasoning. |
| Aggregation layer + the paid upgrade path | **OpenRouter** | One API key routes to 28+ models, including a free pool (DeepSeek R1, Llama 3.3 70B, Qwen3, Gemma 3, Gemini Flash) for overflow/failover, and the exact same integration reaches paid Claude or GPT-4o the moment budget allows — just change `OPENROUTER_CHAT_MODEL` in `.env`, nothing else. |

`config.py` already has all four sets of keys/model names scaffolded (`GEMINI_*`,
`GROQ_*`, `OPENROUTER_*`, plus unused `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` for direct
paid access later). `LLM_PROVIDER` and `EMBEDDING_PROVIDER` pick which one is active;
switching providers is a `.env` change, not a code change, once `services/llm/` and
`services/embeddings/` are implemented in Phase 3.

## Why this combination and not a single provider

Free tiers are rate-limited (Gemini: 10–15 requests/minute; Groq: ~30 requests/minute),
which a single busy student session (chat + background flashcard/quiz generation) can hit.
Splitting "interactive chat" (Gemini) from "bulk background generation" (Groq) keeps the
student-facing chat responsive even when a big quiz batch is being generated, and
OpenRouter's free pool is the shock absorber if either primary is temporarily throttled.
All three are reachable through the same `LLMProvider` interface, so this is a routing
decision inside `services/llm/factory.py`, not three different integrations.

## Rate limits, current as of this writing (verify before relying on them for capacity planning — free-tier limits change often)

- Gemini API: ~10–15 requests/minute, ~1,500 requests/day on Flash, no credit card, up to 1M token context.
- Groq: ~30 requests/minute free on Llama 3.3 70B, no credit card.
- OpenRouter free tier: 20 requests/minute, 50–1,000 requests/day across 28+ free models, no credit card.
- Gemini Embedding: ~1,500 requests/day, 10M tokens/minute, no credit card.

Sources:
- [Free LLM API in 2026: 13 Options Ranked and Compared — OpenRouter Blog](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/)
- [Best Free LLM APIs in 2026 — Compare Free Inference Tiers, Rate Limits & Models](https://agentdeals.dev/free-llm-apis)
- [OpenRouter Free Tier 2026: Rate Limits, Models, BYOK](https://klymentiev.com/blog/openrouter-free-tier)
- [Best Free LLM API Tiers in 2026: Groq, Cerebras, GitHub Models & More](https://wetheflywheel.com/en/ai-model-access/free-llm-api-tiers-2026/)
- [Best Free Embedding Models & APIs in 2026](https://www.edenai.co/post/top-free-embedding-tools-apis-and-open-source-models)
- [Text Embedding Models 2026: Google vs OpenAI vs Voyage](https://tokenmix.ai/blog/text-embedding-models-comparison)

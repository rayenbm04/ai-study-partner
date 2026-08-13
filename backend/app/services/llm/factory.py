from app.core.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.fallback_provider import FallbackLLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_compatible_provider import OpenAICompatibleProvider

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_OPENAI_BASE_URL = "https://api.openai.com/v1"
_CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"

# Cerebras' current lineup (gpt-oss-120b, llama3.1-8b) is text-only — unlike
# Groq (a separate vision-capable lineup, see groq_vision_model) or
# Gemini/OpenAI (natively multimodal chat models). Selecting
# LLM_PROVIDER=cerebras with no LLM_FALLBACK_PROVIDER set means any vision
# call (scanned PDF pages, standalone images) fails outright — see
# docs/LLM_PROVIDERS.md.
_NO_VISION_PROVIDERS = {"cerebras"}


def _build(settings: Settings, *, provider: str, chat_model: str) -> LLMProvider:
    if provider == "gemini":
        return GeminiProvider(api_key=settings.gemini_api_key, model=chat_model)
    if provider == "groq":
        return OpenAICompatibleProvider(
            api_key=settings.groq_api_key,
            base_url=_GROQ_BASE_URL,
            model=chat_model,
            provider_name="groq",
            vision_model=settings.groq_vision_model,
        )
    if provider == "cerebras":
        # No vision_model — see _NO_VISION_PROVIDERS above. A vision call
        # against this provider will fail with an API-side "model doesn't
        # support images" error unless FallbackLLMProvider routes around it.
        return OpenAICompatibleProvider(
            api_key=settings.cerebras_api_key,
            base_url=_CEREBRAS_BASE_URL,
            model=chat_model,
            provider_name="cerebras",
        )
    if provider == "openrouter":
        return OpenAICompatibleProvider(
            api_key=settings.openrouter_api_key,
            base_url=_OPENROUTER_BASE_URL,
            model=chat_model,
            provider_name="openrouter",
            vision_model=settings.openrouter_vision_model or None,
        )
    if provider == "openai":
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key,
            base_url=_OPENAI_BASE_URL,
            model=chat_model,
            provider_name="openai",
            vision_model=settings.openai_vision_model or None,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Expected one of: gemini, groq, cerebras, openrouter, openai."
    )


# One resolver per provider, shared by build_llm_provider (main model) and
# build_simple_llm_provider (cheap model) below, and reused again to resolve
# whichever provider LLM_FALLBACK_PROVIDER names — see _with_fallback.
_MAIN_CHAT_MODELS = {
    "gemini": lambda s: s.gemini_chat_model,
    "groq": lambda s: s.groq_chat_model,
    "cerebras": lambda s: s.cerebras_chat_model,
    "openrouter": lambda s: s.openrouter_chat_model,
    "openai": lambda s: s.openai_chat_model,
}

_SIMPLE_CHAT_MODELS = {
    "gemini": lambda s: s.gemini_simple_chat_model or s.gemini_chat_model,
    "groq": lambda s: s.groq_simple_chat_model or s.groq_chat_model,
    "cerebras": lambda s: s.cerebras_simple_chat_model or s.cerebras_chat_model,
    "openrouter": lambda s: s.openrouter_simple_chat_model or s.openrouter_chat_model,
    "openai": lambda s: s.openai_simple_chat_model or s.openai_chat_model,
}


def _build_for_provider(settings: Settings, *, provider: str, models: dict) -> LLMProvider:
    resolver = models.get(provider)
    if resolver is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Expected one of: {', '.join(models)}."
        )
    return _build(settings, provider=provider, chat_model=resolver(settings))


def _with_fallback(settings: Settings, *, primary: LLMProvider, models: dict) -> LLMProvider:
    """Wraps `primary` in a FallbackLLMProvider using LLM_FALLBACK_PROVIDER
    when one is configured and differs from LLM_PROVIDER itself — e.g.
    LLM_PROVIDER=cerebras + LLM_FALLBACK_PROVIDER=groq, see
    docs/LLM_PROVIDERS.md. Returns `primary` unchanged (no wrapping at all)
    when LLM_FALLBACK_PROVIDER is unset, which is the default."""
    fallback_name = settings.llm_fallback_provider
    if not fallback_name or fallback_name == settings.llm_provider:
        return primary
    fallback = _build_for_provider(settings, provider=fallback_name, models=models)
    return FallbackLLMProvider(
        primary=primary,
        fallback=fallback,
        primary_supports_vision=settings.llm_provider not in _NO_VISION_PROVIDERS,
    )


def build_llm_provider(settings: Settings) -> LLMProvider:
    """The main/"complex" text model — tutoring answers, exam-question
    grading, and anything else that needs real reasoning quality."""
    primary = _build_for_provider(settings, provider=settings.llm_provider, models=_MAIN_CHAT_MODELS)
    return _with_fallback(settings, primary=primary, models=_MAIN_CHAT_MODELS)


def build_simple_llm_provider(settings: Settings) -> LLMProvider:
    """A cheaper/faster text model for mechanical tasks: concept tagging,
    document classification, summaries, flashcard/quiz generation, and RAG
    query rewriting (condense/HyDE/multi-query/rerank) — none of these need
    the main model's reasoning depth, and they're also the calls that fire
    most often during ingestion and chat. Falls back to the main chat model
    per-provider when no simple-tier model is configured (the *_simple_chat_model
    settings default to "" for providers where guessing a model name isn't
    safe — see app/core/config.py)."""
    primary = _build_for_provider(settings, provider=settings.llm_provider, models=_SIMPLE_CHAT_MODELS)
    return _with_fallback(settings, primary=primary, models=_SIMPLE_CHAT_MODELS)

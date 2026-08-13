from app.core.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_compatible_provider import OpenAICompatibleProvider

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_OPENAI_BASE_URL = "https://api.openai.com/v1"


def _build(settings: Settings, *, chat_model: str) -> LLMProvider:
    provider = settings.llm_provider

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

    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Expected one of: gemini, groq, openrouter, openai.")


def build_llm_provider(settings: Settings) -> LLMProvider:
    """The main/"complex" text model — tutoring answers, exam-question
    grading, and anything else that needs real reasoning quality."""
    chat_models = {
        "gemini": settings.gemini_chat_model,
        "groq": settings.groq_chat_model,
        "openrouter": settings.openrouter_chat_model,
        "openai": settings.openai_chat_model,
    }
    return _build(settings, chat_model=chat_models.get(settings.llm_provider, settings.groq_chat_model))


def build_simple_llm_provider(settings: Settings) -> LLMProvider:
    """A cheaper/faster text model for mechanical tasks: concept tagging,
    document classification, summaries, flashcard/quiz generation, and RAG
    query rewriting (condense/HyDE/multi-query/rerank) — none of these need
    the main model's reasoning depth, and they're also the calls that fire
    most often during ingestion and chat. Falls back to the main chat model
    per-provider when no simple-tier model is configured (the *_simple_chat_model
    settings default to "" for providers where guessing a model name isn't
    safe — see app/core/config.py)."""
    simple_models = {
        "gemini": settings.gemini_simple_chat_model or settings.gemini_chat_model,
        "groq": settings.groq_simple_chat_model or settings.groq_chat_model,
        "openrouter": settings.openrouter_simple_chat_model or settings.openrouter_chat_model,
        "openai": settings.openai_simple_chat_model or settings.openai_chat_model,
    }
    return _build(settings, chat_model=simple_models.get(settings.llm_provider, settings.groq_simple_chat_model))

from app.core.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_compatible_provider import OpenAICompatibleProvider

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_OPENAI_BASE_URL = "https://api.openai.com/v1"


def build_llm_provider(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider

    if provider == "gemini":
        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_chat_model)
    if provider == "groq":
        return OpenAICompatibleProvider(
            api_key=settings.groq_api_key, base_url=_GROQ_BASE_URL, model=settings.groq_chat_model, provider_name="groq"
        )
    if provider == "openrouter":
        return OpenAICompatibleProvider(
            api_key=settings.openrouter_api_key,
            base_url=_OPENROUTER_BASE_URL,
            model=settings.openrouter_chat_model,
            provider_name="openrouter",
        )
    if provider == "openai":
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key, base_url=_OPENAI_BASE_URL, model=settings.openai_chat_model, provider_name="openai"
        )

    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Expected one of: gemini, groq, openrouter, openai.")

import pytest

from app.core.config import Settings
from app.services.llm.factory import build_llm_provider, build_simple_llm_provider


def _settings(**overrides) -> Settings:
    return Settings(groq_api_key="test-key", gemini_api_key="test-key", **overrides)


def test_build_llm_provider_uses_main_groq_model():
    provider = build_llm_provider(_settings(llm_provider="groq", groq_chat_model="llama-3.3-70b-versatile"))
    assert provider.model_name == "llama-3.3-70b-versatile"


def test_build_simple_llm_provider_uses_simple_groq_model():
    provider = build_simple_llm_provider(
        _settings(llm_provider="groq", groq_simple_chat_model="llama-3.1-8b-instant")
    )
    assert provider.model_name == "llama-3.1-8b-instant"


def test_build_simple_llm_provider_falls_back_to_main_model_when_unset():
    """Gemini/OpenRouter/OpenAI default their *_simple_chat_model to "" —
    unset means "reuse the main chat model", not "crash" or "use garbage"."""
    provider = build_simple_llm_provider(
        _settings(llm_provider="gemini", gemini_chat_model="gemini-2.5-flash", gemini_simple_chat_model="")
    )
    assert provider.model_name == "gemini-2.5-flash"


def test_build_simple_llm_provider_uses_configured_gemini_simple_model():
    provider = build_simple_llm_provider(
        _settings(
            llm_provider="gemini", gemini_chat_model="gemini-2.5-flash",
            gemini_simple_chat_model="gemini-2.5-flash-lite",
        )
    )
    assert provider.model_name == "gemini-2.5-flash-lite"


def test_build_llm_provider_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        build_llm_provider(_settings(llm_provider="not-a-real-provider"))

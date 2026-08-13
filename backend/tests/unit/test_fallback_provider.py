import httpx
import pytest
from openai import RateLimitError

from app.services.llm.base import LLMProvider
from app.services.llm.fallback_provider import FallbackLLMProvider


def _rate_limit_error(message: str = "rate limited"):
    request = httpx.Request("POST", "https://api.cerebras.ai/v1/chat/completions")
    response = httpx.Response(429, headers={}, request=request)
    return RateLimitError(message, response=response, body=None)


class _FakeLLMProvider(LLMProvider):
    """Records calls; raises on complete()/complete_vision() when told to,
    otherwise returns a fixed marker string so tests can tell which provider
    actually answered."""

    def __init__(self, *, name: str, raises: Exception | None = None):
        self._name = name
        self._raises = raises
        self.complete_calls = 0
        self.vision_calls = 0

    @property
    def model_name(self) -> str:
        return self._name

    async def complete(self, **kwargs) -> str:
        self.complete_calls += 1
        if self._raises is not None:
            raise self._raises
        return f"{self._name}-answer"

    async def complete_vision(self, **kwargs) -> str:
        self.vision_calls += 1
        if self._raises is not None:
            raise self._raises
        return f"{self._name}-vision-answer"


@pytest.mark.asyncio
async def test_complete_uses_primary_when_it_succeeds():
    primary = _FakeLLMProvider(name="cerebras")
    fallback = _FakeLLMProvider(name="groq")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    result = await provider.complete(prompt="hi")

    assert result == "cerebras-answer"
    assert primary.complete_calls == 1
    assert fallback.complete_calls == 0


@pytest.mark.asyncio
async def test_complete_falls_back_on_primary_rate_limit():
    primary = _FakeLLMProvider(name="cerebras", raises=_rate_limit_error())
    fallback = _FakeLLMProvider(name="groq")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    result = await provider.complete(prompt="hi")

    assert result == "groq-answer"
    assert primary.complete_calls == 1
    assert fallback.complete_calls == 1


@pytest.mark.asyncio
async def test_complete_propagates_non_rate_limit_errors_without_falling_back():
    primary = _FakeLLMProvider(name="cerebras", raises=ValueError("boom"))
    fallback = _FakeLLMProvider(name="groq")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    with pytest.raises(ValueError, match="boom"):
        await provider.complete(prompt="hi")

    assert fallback.complete_calls == 0


@pytest.mark.asyncio
async def test_complete_vision_uses_primary_when_it_supports_vision():
    primary = _FakeLLMProvider(name="groq")
    fallback = _FakeLLMProvider(name="openai")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback, primary_supports_vision=True)

    result = await provider.complete_vision(image_bytes=b"x", mime_type="image/png", prompt="describe")

    assert result == "groq-vision-answer"
    assert fallback.vision_calls == 0


@pytest.mark.asyncio
async def test_complete_vision_routes_straight_to_fallback_when_primary_has_no_vision_model():
    """Cerebras has no vision-capable model at all — routing directly to the
    fallback avoids a guaranteed-to-fail call against Cerebras first."""
    primary = _FakeLLMProvider(name="cerebras")
    fallback = _FakeLLMProvider(name="groq")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback, primary_supports_vision=False)

    result = await provider.complete_vision(image_bytes=b"x", mime_type="image/png", prompt="describe")

    assert result == "groq-vision-answer"
    assert primary.vision_calls == 0
    assert fallback.vision_calls == 1


@pytest.mark.asyncio
async def test_complete_vision_falls_back_on_primary_rate_limit():
    primary = _FakeLLMProvider(name="groq", raises=_rate_limit_error())
    fallback = _FakeLLMProvider(name="openai")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback, primary_supports_vision=True)

    result = await provider.complete_vision(image_bytes=b"x", mime_type="image/png", prompt="describe")

    assert result == "openai-vision-answer"
    assert primary.vision_calls == 1
    assert fallback.vision_calls == 1


def test_model_name_reports_the_primary_providers_model():
    primary = _FakeLLMProvider(name="cerebras")
    fallback = _FakeLLMProvider(name="groq")
    provider = FallbackLLMProvider(primary=primary, fallback=fallback)

    assert provider.model_name == "cerebras"

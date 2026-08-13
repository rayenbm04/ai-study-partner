from google import genai
from google.genai import types

from app.services.llm.base import LLMProvider
from app.services.llm.gemini_errors import is_daily_quota_exhausted as _is_daily_quota_exhausted
from app.services.llm.gemini_errors import is_rate_limit_error as _is_rate_limit_error
from app.services.llm.gemini_errors import parse_retry_delay as _parse_retry_delay
from app.services.llm.rate_limit_retry import retry_on_rate_limit


class GeminiProvider(LLMProvider):
    def __init__(self, *, api_key: str, model: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        response_json: bool = False,
    ) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json" if response_json else "text/plain",
        )
        response = await retry_on_rate_limit(
            lambda: self._client.aio.models.generate_content(model=self._model, contents=prompt, config=config),
            is_rate_limit_error=_is_rate_limit_error,
            parse_retry_delay=_parse_retry_delay,
            provider_name="Gemini",
            is_unrecoverable=_is_daily_quota_exhausted,
        )
        return response.text or ""

    async def complete_vision(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        max_output_tokens: int = 2048,
    ) -> str:
        # Gemini Flash is natively multimodal — no separate vision model/config
        # needed, unlike the local Ollama + fallback cloud vision model setup
        # this replaces.
        config = types.GenerateContentConfig(temperature=0.1, max_output_tokens=max_output_tokens)
        response = await retry_on_rate_limit(
            lambda: self._client.aio.models.generate_content(
                model=self._model,
                contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
                config=config,
            ),
            is_rate_limit_error=_is_rate_limit_error,
            parse_retry_delay=_parse_retry_delay,
            provider_name="Gemini",
            is_unrecoverable=_is_daily_quota_exhausted,
        )
        return response.text or ""

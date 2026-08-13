"""Wraps a primary LLMProvider with a fallback provider for when the primary
is rate-limited or, for a text-only provider like Cerebras, doesn't support
vision at all — see docs/LLM_PROVIDERS.md's "Cerebras + Groq" combination.
Built by app/services/llm/factory.py when LLM_FALLBACK_PROVIDER is set;
LLM_FALLBACK_PROVIDER unset (the default) means no wrapping happens at all
and callers get the primary provider directly, same as before this existed.

Both `primary` and `fallback` need to be OpenAICompatibleProvider instances
(Groq, Cerebras, OpenRouter, OpenAI) for the rate-limit fallback to actually
trigger — they're the ones that raise `openai.RateLimitError`. Gemini raises
its own provider-specific exceptions (see gemini_errors.py) and isn't a
supported primary/fallback here; it doesn't need this anyway; its free tier
is already the most generous of the four (see docs/LLM_PROVIDERS.md).
"""
import logging

from openai import RateLimitError

from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class FallbackLLMProvider(LLMProvider):
    def __init__(self, *, primary: LLMProvider, fallback: LLMProvider, primary_supports_vision: bool = True):
        self._primary = primary
        self._fallback = fallback
        # Cerebras' current lineup (gpt-oss-120b, llama3.1-8b) is text-only —
        # routing every vision call straight to the fallback provider avoids
        # a guaranteed-to-fail call-then-catch round trip against Cerebras.
        self._primary_supports_vision = primary_supports_vision

    @property
    def model_name(self) -> str:
        return self._primary.model_name

    async def complete(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        response_json: bool = False,
    ) -> str:
        try:
            return await self._primary.complete(
                prompt=prompt, system=system, temperature=temperature,
                max_output_tokens=max_output_tokens, response_json=response_json,
            )
        except RateLimitError:
            logger.warning(
                "%s exhausted its rate limit/quota — falling back to %s.",
                self._primary.model_name, self._fallback.model_name,
            )
            return await self._fallback.complete(
                prompt=prompt, system=system, temperature=temperature,
                max_output_tokens=max_output_tokens, response_json=response_json,
            )

    async def complete_vision(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        max_output_tokens: int = 2048,
    ) -> str:
        if not self._primary_supports_vision:
            return await self._fallback.complete_vision(
                image_bytes=image_bytes, mime_type=mime_type, prompt=prompt, max_output_tokens=max_output_tokens,
            )
        try:
            return await self._primary.complete_vision(
                image_bytes=image_bytes, mime_type=mime_type, prompt=prompt, max_output_tokens=max_output_tokens,
            )
        except RateLimitError:
            logger.warning(
                "%s exhausted its rate limit/quota on a vision call — falling back to %s.",
                self._primary.model_name, self._fallback.model_name,
            )
            return await self._fallback.complete_vision(
                image_bytes=image_bytes, mime_type=mime_type, prompt=prompt, max_output_tokens=max_output_tokens,
            )

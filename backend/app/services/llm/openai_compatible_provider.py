import base64

from openai import AsyncOpenAI, RateLimitError

from app.services.llm.base import LLMProvider
from app.services.llm.rate_limit_retry import retry_on_rate_limit


def _is_rate_limit_error(exc: Exception) -> bool:
    return isinstance(exc, RateLimitError)


def _parse_retry_delay(exc: Exception) -> float | None:
    """Groq/OpenAI/OpenRouter send a standard Retry-After header (seconds) on
    a 429. Falls back to rate_limit_retry's default if it's missing or comes
    back as an HTTP-date instead of a delta (not worth parsing that format
    here — the default is a reasonable guess either way)."""
    if not isinstance(exc, RateLimitError):
        return None
    header = exc.response.headers.get("retry-after")
    if not header:
        return None
    try:
        return float(header)
    except ValueError:
        return None


# Same detection rag-backend/ (this project's predecessor) already uses for
# Groq: a 429 whose message names a per-day/TPD quota won't recover within
# any reasonable retry window, unlike a TPM/RPM one that resets in seconds.
_DAILY_QUOTA_MARKERS = ("per day", "tokens per day", "tpd")


def _is_daily_quota_exhausted(exc: Exception) -> bool:
    if not isinstance(exc, RateLimitError):
        return False
    message = str(getattr(exc, "message", "") or exc).lower()
    return any(marker in message for marker in _DAILY_QUOTA_MARKERS)


class OpenAICompatibleProvider(LLMProvider):
    """Groq, OpenRouter, and OpenAI itself all speak the OpenAI chat-completions
    API, so one client — pointed at a different base_url and key — covers all
    three instead of three separate SDK integrations."""

    def __init__(
        self, *, api_key: str, base_url: str, model: str, provider_name: str, vision_model: str | None = None
    ):
        if not api_key:
            raise ValueError(f"{provider_name.upper()}_API_KEY is not set.")
        # The SDK's defaults (600s request timeout, 2 retries with unbounded
        # provider-dictated backoff) are tuned for paid tiers with generous
        # quotas — on a free tier that's hit a daily/hourly quota, a single
        # 429's Retry-After can itself be very long, and the SDK will sleep
        # that long *before each retry*, silently stalling an ingestion call
        # for a very long time. Turning off the SDK's own retries and using a
        # short per-request timeout bounds a genuine failure (bad request,
        # auth, 5xx) to seconds. Rate limits specifically get our own bounded
        # retry instead (see rate_limit_retry.py) — most free-tier 429s are a
        # short per-minute quota, not an exhausted daily one, so a couple of
        # short, capped waits gives them a real chance to clear.
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=0)
        self._model = model
        self._provider_name = provider_name
        # Chat and vision aren't guaranteed to be the same model on every
        # OpenAI-compatible backend — Groq in particular splits them into
        # separate lineups. Falls back to the chat model when the two happen
        # to coincide (OpenAI, most OpenRouter models).
        self._vision_model = vision_model or model

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
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await retry_on_rate_limit(
            lambda: self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_output_tokens,
                response_format={"type": "json_object"} if response_json else None,
            ),
            is_rate_limit_error=_is_rate_limit_error,
            parse_retry_delay=_parse_retry_delay,
            provider_name=self._provider_name,
            is_unrecoverable=_is_daily_quota_exhausted,
        )
        return response.choices[0].message.content or ""

    async def complete_vision(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        max_output_tokens: int = 2048,
    ) -> str:
        # Standard OpenAI-compatible vision message shape — same content-part
        # format Groq's and OpenRouter's vision-capable models accept.
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        response = await retry_on_rate_limit(
            lambda: self._client.chat.completions.create(
                model=self._vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=max_output_tokens,
            ),
            is_rate_limit_error=_is_rate_limit_error,
            parse_retry_delay=_parse_retry_delay,
            provider_name=self._provider_name,
            is_unrecoverable=_is_daily_quota_exhausted,
        )
        return response.choices[0].message.content or ""

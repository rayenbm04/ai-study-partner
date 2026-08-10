import re

from google import genai
from google.genai import errors, types

from app.services.llm.base import LLMProvider
from app.services.llm.rate_limit_retry import retry_on_rate_limit

_RETRY_DELAY_PATTERN = re.compile(r"([\d.]+)")


def _is_rate_limit_error(exc: Exception) -> bool:
    return isinstance(exc, errors.ClientError) and exc.code == 429


def _parse_retry_delay(exc: Exception) -> float | None:
    """Gemini's 429 body includes a RetryInfo detail with a retryDelay like
    '50s' — almost exactly how long until the free-tier per-minute quota
    resets. Falls back to rate_limit_retry's default if this can't be found
    or parsed (error shape isn't officially guaranteed, so this is best-effort)."""
    if not isinstance(exc, errors.APIError) or not isinstance(exc.details, dict):
        return None
    details = exc.details.get("error", {}).get("details", [])
    for item in details:
        if isinstance(item, dict) and str(item.get("@type", "")).endswith("RetryInfo"):
            match = _RETRY_DELAY_PATTERN.match(str(item.get("retryDelay", "")))
            if match:
                return float(match.group(1))
    return None


def _is_daily_quota_exhausted(exc: Exception) -> bool:
    """Gemini's QuotaFailure detail names the specific quota that was hit —
    e.g. quotaId 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier' for a
    per-minute limit (worth retrying, resets in under a minute) vs. one
    containing 'PerDay' (won't reset until tomorrow, no point retrying).
    Falls back to "retry it" (False) if the shape can't be read — retrying a
    genuinely-exhausted quota wastes at most a few bounded attempts, which is
    a much smaller cost than wrongly giving up on a transient per-minute one."""
    if not isinstance(exc, errors.APIError) or not isinstance(exc.details, dict):
        return False
    details = exc.details.get("error", {}).get("details", [])
    for item in details:
        if not isinstance(item, dict) or not str(item.get("@type", "")).endswith("QuotaFailure"):
            continue
        for violation in item.get("violations", []):
            quota_id = str(violation.get("quotaId", "")) if isinstance(violation, dict) else ""
            if "day" in quota_id.lower():
                return True
    return False


class GeminiProvider(LLMProvider):
    def __init__(self, *, api_key: str, model: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self._client = genai.Client(api_key=api_key)
        self._model = model

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

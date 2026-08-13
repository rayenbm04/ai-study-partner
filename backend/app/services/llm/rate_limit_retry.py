"""Shared bounded retry-on-429 helper for LLM providers.

Free-tier quotas are easy to blow through during ingestion, which fires one
LLM call per parent chunk (concept tagging) plus one per low-text PDF page
(vision fallback) plus one classification call — a single multi-page scanned
document can trigger 20+ calls in quick succession. Gemini's free tier for
gemini-2.5-flash, for example, allows only 5 requests/minute; Groq's varies
by model but is similarly tight on some models.

These rate-limit errors are usually transient and the provider tells us
almost exactly how long until the quota resets (Gemini's RetryInfo.retryDelay,
Groq/OpenAI's Retry-After header) — so a short, bounded retry gives real
transient limits a fair chance to clear on their own. This is deliberately
NOT the SDK's own default retry behavior (which, respecting the same
provider-supplied delay with more attempts and no cap, can compound into a
multi-minute stall hidden inside a single call — see the ingestion timeout
fix in openai_compatible_provider.py) — bounded attempt count and a capped
per-attempt wait keep the worst case predictable.

One rate limit is NOT worth retrying at all: a daily/monthly quota that's
fully exhausted. Retrying that just burns the whole MAX_ATTEMPTS budget
(minutes) before failing anyway, since nothing changes until the quota resets
tomorrow. rag-backend/ (this project's predecessor) already learned this the
hard way and distinguishes "per day"/TPD limits (fail immediately) from
per-minute ones (worth retrying) — `is_unrecoverable` below is the same idea,
ported so ingestion fails fast instead of stalling for minutes on a quota
that was never going to recover in time anyway.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import settings

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

# Env-configurable (MAX_RETRIES / INITIAL_RETRY_DELAY / MAX_RETRY_DELAY) so a
# stricter or more generous provider tier can be dialed in without a code
# change — see Settings in app/core/config.py for the full rationale.
MAX_ATTEMPTS = settings.max_retries
DEFAULT_DELAY_SECONDS = settings.initial_retry_delay
MAX_DELAY_SECONDS = settings.max_retry_delay


async def retry_on_rate_limit(
    call: Callable[[], Awaitable[_T]],
    *,
    is_rate_limit_error: Callable[[Exception], bool],
    parse_retry_delay: Callable[[Exception], float | None],
    provider_name: str,
    is_unrecoverable: Callable[[Exception], bool] | None = None,
) -> _T:
    """Calls `call()`, retrying up to MAX_ATTEMPTS total on errors
    `is_rate_limit_error` recognizes as a 429. Waits `parse_retry_delay`'s
    result between attempts if given (falling back to DEFAULT_DELAY_SECONDS),
    capped at MAX_DELAY_SECONDS so one very long provider-suggested delay
    can't reintroduce the multi-minute stall this exists to avoid. Any other
    exception, or a rate limit on the final attempt, propagates immediately —
    as does any rate limit `is_unrecoverable` flags as a quota that won't
    reset soon enough to matter (skips straight to raising, no sleep, even on
    the first attempt)."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await call()
        except Exception as exc:
            if not is_rate_limit_error(exc):
                raise
            if is_unrecoverable is not None and is_unrecoverable(exc):
                logger.warning(
                    "%s rate-limited by what looks like an exhausted daily/long-window quota — "
                    "failing immediately rather than retrying (attempt %d/%d).",
                    provider_name, attempt, MAX_ATTEMPTS,
                )
                raise
            if attempt == MAX_ATTEMPTS:
                raise
            delay = parse_retry_delay(exc)
            if delay is None:
                delay = DEFAULT_DELAY_SECONDS
            delay = min(delay, MAX_DELAY_SECONDS)
            logger.warning(
                "%s rate-limited (attempt %d/%d) — retrying in %.0fs.",
                provider_name, attempt, MAX_ATTEMPTS, delay,
            )
            await asyncio.sleep(delay)
    raise AssertionError("unreachable — loop above always returns or raises")

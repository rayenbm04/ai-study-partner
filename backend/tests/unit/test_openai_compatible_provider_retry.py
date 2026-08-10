import httpx
from openai import RateLimitError

from app.services.llm.openai_compatible_provider import (
    _is_daily_quota_exhausted,
    _is_rate_limit_error,
    _parse_retry_delay,
)


def _rate_limit_error(*, retry_after: str | None = "12", message: str = "rate limited"):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    response = httpx.Response(429, headers=headers, request=request)
    return RateLimitError(message, response=response, body=None)


def test_is_rate_limit_error_true_for_rate_limit_error():
    assert _is_rate_limit_error(_rate_limit_error(retry_after="12")) is True


def test_is_rate_limit_error_false_for_unrelated_exception():
    assert _is_rate_limit_error(ValueError("nope")) is False


def test_parse_retry_delay_reads_retry_after_header():
    assert _parse_retry_delay(_rate_limit_error(retry_after="12")) == 12.0


def test_parse_retry_delay_returns_none_when_header_missing():
    assert _parse_retry_delay(_rate_limit_error(retry_after=None)) is None


def test_parse_retry_delay_returns_none_for_non_numeric_header():
    # Retry-After can legally be an HTTP-date instead of a delta-seconds
    # value — not worth parsing that format, the caller falls back to a
    # sane default delay instead.
    assert _parse_retry_delay(_rate_limit_error(retry_after="Wed, 21 Oct 2026 07:28:00 GMT")) is None


def test_parse_retry_delay_returns_none_for_unrelated_exception():
    assert _parse_retry_delay(ValueError("nope")) is None


def test_is_daily_quota_exhausted_true_for_per_day_message():
    exc = _rate_limit_error(
        message="Rate limit reached for model `x` on tokens per day (TPD): Limit 100000, Used 100000."
    )
    assert _is_daily_quota_exhausted(exc) is True


def test_is_daily_quota_exhausted_false_for_per_minute_message():
    exc = _rate_limit_error(
        message="Rate limit reached for model `x` on requests per minute (RPM): Limit 30, Used 30."
    )
    assert _is_daily_quota_exhausted(exc) is False


def test_is_daily_quota_exhausted_false_for_unrelated_exception():
    assert _is_daily_quota_exhausted(ValueError("nope")) is False

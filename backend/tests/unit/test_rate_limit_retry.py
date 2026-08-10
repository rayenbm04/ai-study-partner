import pytest

from app.services.llm.rate_limit_retry import (
    DEFAULT_DELAY_SECONDS,
    MAX_ATTEMPTS,
    MAX_DELAY_SECONDS,
    retry_on_rate_limit,
)


class _RateLimitError(Exception):
    pass


class _OtherError(Exception):
    pass


def _record_sleep(monkeypatch, sleeps: list[float]):
    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("app.services.llm.rate_limit_retry.asyncio.sleep", fake_sleep)


async def test_returns_result_immediately_when_no_error():
    async def call():
        return "ok"

    result = await retry_on_rate_limit(
        call, is_rate_limit_error=lambda e: True, parse_retry_delay=lambda e: None, provider_name="test"
    )
    assert result == "ok"


async def test_retries_and_succeeds_within_max_attempts(monkeypatch):
    sleeps: list[float] = []
    _record_sleep(monkeypatch, sleeps)
    attempts = {"count": 0}

    async def call():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise _RateLimitError()
        return "ok"

    result = await retry_on_rate_limit(
        call,
        is_rate_limit_error=lambda e: isinstance(e, _RateLimitError),
        parse_retry_delay=lambda e: 5.0,
        provider_name="test",
    )
    assert result == "ok"
    assert attempts["count"] == 2
    assert sleeps == [5.0]


async def test_gives_up_after_max_attempts_and_raises_last_error(monkeypatch):
    sleeps: list[float] = []
    _record_sleep(monkeypatch, sleeps)
    attempts = {"count": 0}

    async def call():
        attempts["count"] += 1
        raise _RateLimitError()

    with pytest.raises(_RateLimitError):
        await retry_on_rate_limit(
            call,
            is_rate_limit_error=lambda e: isinstance(e, _RateLimitError),
            parse_retry_delay=lambda e: 1.0,
            provider_name="test",
        )
    assert attempts["count"] == MAX_ATTEMPTS
    # Sleeps happen between attempts, not after the last one.
    assert len(sleeps) == MAX_ATTEMPTS - 1


async def test_non_rate_limit_error_propagates_without_retrying(monkeypatch):
    sleeps: list[float] = []
    _record_sleep(monkeypatch, sleeps)
    attempts = {"count": 0}

    async def call():
        attempts["count"] += 1
        raise _OtherError("boom")

    with pytest.raises(_OtherError):
        await retry_on_rate_limit(
            call,
            is_rate_limit_error=lambda e: isinstance(e, _RateLimitError),
            parse_retry_delay=lambda e: 1.0,
            provider_name="test",
        )
    assert attempts["count"] == 1
    assert sleeps == []


async def test_missing_parsed_delay_falls_back_to_default(monkeypatch):
    sleeps: list[float] = []
    _record_sleep(monkeypatch, sleeps)

    async def call():
        if len(sleeps) == 0:
            raise _RateLimitError()
        return "ok"

    await retry_on_rate_limit(
        call,
        is_rate_limit_error=lambda e: isinstance(e, _RateLimitError),
        parse_retry_delay=lambda e: None,
        provider_name="test",
    )
    assert sleeps == [DEFAULT_DELAY_SECONDS]


async def test_unrecoverable_rate_limit_fails_immediately_without_sleeping(monkeypatch):
    sleeps: list[float] = []
    _record_sleep(monkeypatch, sleeps)
    attempts = {"count": 0}

    async def call():
        attempts["count"] += 1
        raise _RateLimitError()

    with pytest.raises(_RateLimitError):
        await retry_on_rate_limit(
            call,
            is_rate_limit_error=lambda e: isinstance(e, _RateLimitError),
            parse_retry_delay=lambda e: 1.0,
            provider_name="test",
            is_unrecoverable=lambda e: True,
        )
    # Fails on the very first attempt — no retries burned on a quota that
    # was never going to reset in time anyway.
    assert attempts["count"] == 1
    assert sleeps == []


async def test_recoverable_rate_limit_still_retries_when_is_unrecoverable_given(monkeypatch):
    sleeps: list[float] = []
    _record_sleep(monkeypatch, sleeps)
    attempts = {"count": 0}

    async def call():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise _RateLimitError()
        return "ok"

    result = await retry_on_rate_limit(
        call,
        is_rate_limit_error=lambda e: isinstance(e, _RateLimitError),
        parse_retry_delay=lambda e: 5.0,
        provider_name="test",
        is_unrecoverable=lambda e: False,
    )
    assert result == "ok"
    assert attempts["count"] == 2
    assert sleeps == [5.0]


async def test_parsed_delay_is_capped_at_max_delay(monkeypatch):
    sleeps: list[float] = []
    _record_sleep(monkeypatch, sleeps)

    async def call():
        if len(sleeps) == 0:
            raise _RateLimitError()
        return "ok"

    await retry_on_rate_limit(
        call,
        is_rate_limit_error=lambda e: isinstance(e, _RateLimitError),
        parse_retry_delay=lambda e: MAX_DELAY_SECONDS + 500,
        provider_name="test",
    )
    assert sleeps == [MAX_DELAY_SECONDS]

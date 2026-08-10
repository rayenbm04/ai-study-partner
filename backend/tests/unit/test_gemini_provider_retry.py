from google.genai import errors

from app.services.llm.gemini_provider import (
    _is_daily_quota_exhausted,
    _is_rate_limit_error,
    _parse_retry_delay,
)


def _client_error(code, details):
    return errors.ClientError(code, details)


def test_is_rate_limit_error_true_for_429_client_error():
    exc = _client_error(429, {"error": {"status": "RESOURCE_EXHAUSTED"}})
    assert _is_rate_limit_error(exc) is True


def test_is_rate_limit_error_false_for_other_status_codes():
    exc = _client_error(400, {"error": {"status": "INVALID_ARGUMENT"}})
    assert _is_rate_limit_error(exc) is False


def test_is_rate_limit_error_false_for_unrelated_exception():
    assert _is_rate_limit_error(ValueError("nope")) is False


def test_parse_retry_delay_reads_retry_info_seconds():
    exc = _client_error(
        429,
        {
            "error": {
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.Help", "links": []},
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "50s"},
                ],
            }
        },
    )
    assert _parse_retry_delay(exc) == 50.0


def test_parse_retry_delay_returns_none_when_no_retry_info_present():
    exc = _client_error(429, {"error": {"status": "RESOURCE_EXHAUSTED", "details": []}})
    assert _parse_retry_delay(exc) is None


def test_parse_retry_delay_returns_none_for_unrelated_exception():
    assert _parse_retry_delay(ValueError("nope")) is None


def test_is_daily_quota_exhausted_true_for_per_day_quota_id():
    exc = _client_error(
        429,
        {
            "error": {
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {
                                "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                                "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                            }
                        ],
                    }
                ],
            }
        },
    )
    assert _is_daily_quota_exhausted(exc) is True


def test_is_daily_quota_exhausted_false_for_per_minute_quota_id():
    exc = _client_error(
        429,
        {
            "error": {
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {
                                "quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier",
                                "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                            }
                        ],
                    }
                ],
            }
        },
    )
    assert _is_daily_quota_exhausted(exc) is False


def test_is_daily_quota_exhausted_false_when_no_quota_failure_detail():
    exc = _client_error(429, {"error": {"status": "RESOURCE_EXHAUSTED", "details": []}})
    assert _is_daily_quota_exhausted(exc) is False


def test_is_daily_quota_exhausted_false_for_unrelated_exception():
    assert _is_daily_quota_exhausted(ValueError("nope")) is False

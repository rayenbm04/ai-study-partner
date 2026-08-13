"""Shared 429-detection helpers for google-genai's error shape — used by both
GeminiProvider (chat/vision) and GeminiEmbedder, since both hit the same
client and the same error/response format on a rate limit.
"""
import re

from google.genai import errors

_RETRY_DELAY_PATTERN = re.compile(r"([\d.]+)")


def is_rate_limit_error(exc: Exception) -> bool:
    return isinstance(exc, errors.ClientError) and exc.code == 429


def parse_retry_delay(exc: Exception) -> float | None:
    """Gemini's 429 body includes a RetryInfo detail with a retryDelay like
    '50s' — almost exactly how long until the free-tier per-minute quota
    resets. Returns None if this can't be found or parsed (error shape isn't
    officially guaranteed, so this is best-effort)."""
    if not isinstance(exc, errors.APIError) or not isinstance(exc.details, dict):
        return None
    details = exc.details.get("error", {}).get("details", [])
    for item in details:
        if isinstance(item, dict) and str(item.get("@type", "")).endswith("RetryInfo"):
            match = _RETRY_DELAY_PATTERN.match(str(item.get("retryDelay", "")))
            if match:
                return float(match.group(1))
    return None


def is_daily_quota_exhausted(exc: Exception) -> bool:
    """Gemini's QuotaFailure detail names the specific quota that was hit —
    e.g. quotaId 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier' for a
    per-minute limit (worth retrying, resets in under a minute) vs. one
    containing 'PerDay' (won't reset until tomorrow, no point retrying)."""
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

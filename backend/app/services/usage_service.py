"""Per-user usage tracking — the architecture spec #18 asks for, not a
paywall. The backend uses one shared provider API key for every student, so
this is the only place per-user consumption becomes visible at all: every
document upload and AI request records a UsageEvent regardless of whether
limits are enforced.

Limit *enforcement* (check_*) is a config flag away from being live
(settings.usage_limits_enabled) but defaults to off, so today's single-tier
product and existing tests are unaffected — flip it on once free/premium
tiers actually exist, no code change needed.
"""
from datetime import datetime, timezone

from app.core.exceptions import UsageLimitExceededError
from app.domain.repositories.usage_event_repository import UsageEventRepository

# Event types that count against the daily AI-request limit — document
# uploads have their own separate limit (see check_document_limit), and
# concept tagging isn't user-facing so it isn't rate-limited at all.
_AI_REQUEST_EVENT_TYPES = ["chat_message", "summary_generation", "flashcard_generation", "quiz_generation"]


class UsageService:
    def __init__(
        self,
        *,
        usage_repo: UsageEventRepository,
        limits_enabled: bool,
        daily_ai_requests: int,
        daily_documents: int,
    ):
        self._usage = usage_repo
        self._limits_enabled = limits_enabled
        self._daily_ai_requests = daily_ai_requests
        self._daily_documents = daily_documents

    async def record(
        self,
        *,
        user_id: str,
        event_type: str,
        provider: str | None = None,
        model: str | None = None,
        tokens: int | None = None,
        document_id: str | None = None,
    ) -> None:
        await self._usage.record(
            user_id=user_id, event_type=event_type, provider=provider, model=model, tokens=tokens,
            document_id=document_id,
        )

    async def check_ai_request_limit(self, user_id: str) -> None:
        """Raises UsageLimitExceededError if this user has already used
        today's AI-request quota. No-op entirely when usage_limits_enabled
        is False (the default)."""
        if not self._limits_enabled:
            return
        count = await self._usage.count_since(
            user_id=user_id, event_types=_AI_REQUEST_EVENT_TYPES, since=_today_start_utc()
        )
        if count >= self._daily_ai_requests:
            raise UsageLimitExceededError("AI requests", self._daily_ai_requests)

    async def check_document_limit(self, user_id: str) -> None:
        if not self._limits_enabled:
            return
        count = await self._usage.count_since(
            user_id=user_id, event_types=["document_uploaded"], since=_today_start_utc()
        )
        if count >= self._daily_documents:
            raise UsageLimitExceededError("document uploads", self._daily_documents)


def _today_start_utc() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

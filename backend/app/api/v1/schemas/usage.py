from datetime import datetime

from pydantic import BaseModel

from app.services.usage_service import UsageSummary


class UsageSummaryResponse(BaseModel):
    ai_requests_used_today: int
    ai_requests_daily_limit: int
    documents_used_today: int
    documents_daily_limit: int
    limits_enforced: bool
    resets_at: datetime

    @classmethod
    def from_domain(cls, summary: UsageSummary) -> "UsageSummaryResponse":
        return cls(
            ai_requests_used_today=summary.ai_requests_used_today,
            ai_requests_daily_limit=summary.ai_requests_daily_limit,
            documents_used_today=summary.documents_used_today,
            documents_daily_limit=summary.documents_daily_limit,
            limits_enforced=summary.limits_enforced,
            resets_at=summary.resets_at,
        )

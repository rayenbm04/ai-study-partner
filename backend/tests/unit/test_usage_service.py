from app.services.usage_service import UsageService
from tests.unit.fakes import FakeUsageEventRepository


def _service(*, limits_enabled=False, daily_ai_requests=50, daily_documents=5):
    return UsageService(
        usage_repo=FakeUsageEventRepository(),
        limits_enabled=limits_enabled,
        daily_ai_requests=daily_ai_requests,
        daily_documents=daily_documents,
    )


async def test_get_usage_summary_counts_todays_events_by_category():
    service = _service()
    await service.record(user_id="u1", event_type="chat_message")
    await service.record(user_id="u1", event_type="quiz_generation")
    await service.record(user_id="u1", event_type="document_uploaded")
    await service.record(user_id="u2", event_type="chat_message")  # different user, shouldn't count

    summary = await service.get_usage_summary("u1")

    assert summary.ai_requests_used_today == 2
    assert summary.documents_used_today == 1


async def test_get_usage_summary_reports_configured_limits_as_reference_even_when_disabled():
    service = _service(limits_enabled=False, daily_ai_requests=50, daily_documents=5)

    summary = await service.get_usage_summary("u1")

    assert summary.ai_requests_daily_limit == 50
    assert summary.documents_daily_limit == 5
    assert summary.limits_enforced is False


async def test_get_usage_summary_reports_configured_limits_when_enabled():
    service = _service(limits_enabled=True, daily_ai_requests=50, daily_documents=5)

    summary = await service.get_usage_summary("u1")

    assert summary.ai_requests_daily_limit == 50
    assert summary.documents_daily_limit == 5
    assert summary.limits_enforced is True


async def test_get_usage_summary_resets_at_is_next_utc_midnight():
    service = _service()

    summary = await service.get_usage_summary("u1")

    assert summary.resets_at.hour == 0
    assert summary.resets_at.minute == 0
    assert summary.resets_at.second == 0

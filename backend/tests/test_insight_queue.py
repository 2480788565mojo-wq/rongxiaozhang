from unittest.mock import AsyncMock

import pytest

import app.services.insight_service as insight_service
from app.models import ReportType


@pytest.mark.asyncio
async def test_insight_queue_push_is_atomic_and_bounded(monkeypatch):
    redis = AsyncMock()
    redis.eval.return_value = 1
    monkeypatch.setattr(insight_service.settings, "INSIGHT_QUEUE_MAX_LENGTH", 1000)

    job_id = await insight_service.queue_insight_generation(
        redis,
        user_id=1,
        ledger_id=2,
        report_type=ReportType.MONTHLY,
    )

    assert job_id
    assert redis.eval.await_count == 1


@pytest.mark.asyncio
async def test_insight_queue_rejects_when_full(monkeypatch):
    redis = AsyncMock()
    redis.eval.return_value = 0
    monkeypatch.setattr(insight_service.settings, "INSIGHT_QUEUE_MAX_LENGTH", 1000)

    with pytest.raises(insight_service.InsightQueueFull):
        await insight_service.queue_insight_generation(
            redis,
            user_id=1,
            ledger_id=2,
            report_type=ReportType.MONTHLY,
        )

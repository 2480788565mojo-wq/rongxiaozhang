from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.rate_limit import require_rate_limits
from app.core.rate_limit import (
    RateLimitExceeded,
    RateLimitRule,
    acquire_connection_slot,
    consume_rate_limits,
    release_connection_slot,
    touch_connection_slot,
)


@pytest.mark.asyncio
async def test_rate_limit_accepts_requests_within_both_windows():
    redis = AsyncMock()
    redis.eval.side_effect = [[1, 60], [1, 86400]]

    await consume_rate_limits(
        redis,
        "user:1:ai",
        (RateLimitRule("minute", 20, 60), RateLimitRule("day", 200, 86400)),
    )

    assert redis.eval.await_count == 2


@pytest.mark.asyncio
async def test_rate_limit_reports_retry_after_when_exceeded():
    redis = AsyncMock()
    redis.eval.return_value = [21, 37]

    with pytest.raises(RateLimitExceeded) as error:
        await consume_rate_limits(
            redis,
            "user:1:ai",
            (RateLimitRule("minute", 20, 60),),
        )

    assert error.value.retry_after == 37


@pytest.mark.asyncio
async def test_api_rate_limit_returns_429_with_retry_header():
    redis = AsyncMock()
    redis.eval.return_value = [11, 25]

    with pytest.raises(HTTPException) as error:
        await require_rate_limits(
            redis,
            "ip:127.0.0.1:login",
            RateLimitRule("minute", 10, 60),
        )

    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "25"}


@pytest.mark.asyncio
async def test_connection_slot_helpers_use_atomic_redis_scripts():
    redis = AsyncMock()
    redis.eval.return_value = 1

    assert await acquire_connection_slot(
        redis,
        "user:1:sse",
        "connection-1",
        now=100,
        limit=2,
    )
    assert await touch_connection_slot(
        redis,
        "user:1:sse",
        "connection-1",
        now=110,
    )
    await release_connection_slot(redis, "user:1:sse", "connection-1")

    assert redis.eval.await_count == 3

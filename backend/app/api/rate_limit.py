from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.rate_limit import RateLimitExceeded, RateLimitRule, consume_rate_limits


async def require_rate_limits(
    redis: Redis,
    namespace: str,
    *rules: RateLimitRule,
) -> None:
    try:
        await consume_rate_limits(redis, namespace, tuple(rules))
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="操作过于频繁，请稍后再试",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="请求保护服务暂时不可用，请稍后再试",
        ) from exc

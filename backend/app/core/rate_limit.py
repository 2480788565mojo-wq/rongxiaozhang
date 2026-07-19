from dataclasses import dataclass

from redis.asyncio import Redis


RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""

ACQUIRE_SLOT_SCRIPT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[4])
local count = redis.call('ZCARD', KEYS[1])
if count > tonumber(ARGV[5]) then
    redis.call('ZREM', KEYS[1], ARGV[3])
    return 0
end
return 1
"""

TOUCH_SLOT_SCRIPT = """
if redis.call('ZSCORE', KEYS[1], ARGV[2]) then
    redis.call('ZADD', KEYS[1], ARGV[1], ARGV[2])
    redis.call('EXPIRE', KEYS[1], ARGV[3])
    return 1
end
return 0
"""

RELEASE_SLOT_SCRIPT = """
local removed = redis.call('ZREM', KEYS[1], ARGV[1])
if redis.call('ZCARD', KEYS[1]) == 0 then
    redis.call('DEL', KEYS[1])
end
return removed
"""


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, retry_after)
        super().__init__("请求过于频繁")


async def consume_rate_limits(
    redis: Redis,
    namespace: str,
    rules: tuple[RateLimitRule, ...],
) -> None:
    for rule in rules:
        key = f"rate:{namespace}:{rule.name}"
        count, ttl = await redis.eval(
            RATE_LIMIT_SCRIPT,
            1,
            key,
            rule.limit,
            rule.window_seconds,
        )
        if int(count) > rule.limit:
            raise RateLimitExceeded(int(ttl))


async def acquire_connection_slot(
    redis: Redis,
    namespace: str,
    connection_id: str,
    *,
    now: float,
    limit: int,
    ttl_seconds: int = 60,
) -> bool:
    result = await redis.eval(
        ACQUIRE_SLOT_SCRIPT,
        1,
        f"connections:{namespace}",
        now - ttl_seconds,
        now,
        connection_id,
        ttl_seconds,
        limit,
    )
    return bool(result)


async def touch_connection_slot(
    redis: Redis,
    namespace: str,
    connection_id: str,
    *,
    now: float,
    ttl_seconds: int = 60,
) -> bool:
    result = await redis.eval(
        TOUCH_SLOT_SCRIPT,
        1,
        f"connections:{namespace}",
        now,
        connection_id,
        ttl_seconds,
    )
    return bool(result)


async def release_connection_slot(
    redis: Redis,
    namespace: str,
    connection_id: str,
) -> None:
    await redis.eval(
        RELEASE_SLOT_SCRIPT,
        1,
        f"connections:{namespace}",
        connection_id,
    )

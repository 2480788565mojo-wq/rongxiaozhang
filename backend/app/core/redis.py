from datetime import datetime, timezone

from redis.asyncio import ConnectionPool, Redis

from app.config import get_settings


settings = get_settings()
pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
    decode_responses=True,
    # The local Windows Redis 5 server supports RESP2. Redis 6+ also keeps
    # RESP2 compatibility, so this remains portable to the cloud runtime.
    protocol=2,
)


async def get_redis() -> Redis:
    return Redis(connection_pool=pool)


def budget_spent_key(
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
    category: str,
) -> str:
    return f"budget:{user_id}:{ledger_id}:{year}:{month}:{category}"


def budget_limit_key(
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
    category: str,
) -> str:
    return f"budget_limit:{user_id}:{ledger_id}:{year}:{month}:{category}"


async def incr_budget_spent(
    redis: Redis,
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
    category: str,
    amount: float,
) -> float:
    key = budget_spent_key(user_id, ledger_id, year, month, category)
    spent = await redis.incrbyfloat(key, amount)
    if float(spent) < 0:
        await redis.set(key, 0, keepttl=True)
        spent = 0.0

    # Counters are only useful for their month. Keep them long enough for
    # late-arriving requests, then let Redis reclaim the space automatically.
    if await redis.ttl(key) < 0:
        expiry_year = year + 1 if month == 12 else year
        expiry_month = 1 if month == 12 else month + 1
        expiry = datetime(expiry_year, expiry_month, 1, tzinfo=timezone.utc)
        await redis.expireat(key, expiry)

    return float(spent)


async def get_budget_spent(
    redis: Redis,
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
    category: str,
) -> float:
    value = await redis.get(
        budget_spent_key(user_id, ledger_id, year, month, category)
    )
    return float(value) if value is not None else 0.0


async def acquire_ledger_lock(
    redis: Redis,
    ledger_id: int,
    request_id: str,
    ttl: int = 5,
) -> bool:
    acquired = await redis.set(
        f"lock:ledger:{ledger_id}:write",
        request_id,
        nx=True,
        ex=ttl,
    )
    return bool(acquired)


async def release_ledger_lock(
    redis: Redis,
    ledger_id: int,
    request_id: str,
) -> bool:
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    end
    return 0
    """
    released = await redis.eval(
        script,
        1,
        f"lock:ledger:{ledger_id}:write",
        request_id,
    )
    return bool(released)


async def close_redis() -> None:
    await pool.disconnect()

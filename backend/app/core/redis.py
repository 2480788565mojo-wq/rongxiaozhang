import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from uuid import uuid4

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

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


def budget_total_spent_key(
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
) -> str:
    return f"budget_total_spent:{user_id}:{ledger_id}:{year}:{month}"


def budget_total_limit_key(
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
) -> str:
    return f"budget_total_limit:{user_id}:{ledger_id}:{year}:{month}"


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
    expiry_year = year + 1 if month == 12 else year
    expiry_month = 1 if month == 12 else month + 1
    expiry = datetime(expiry_year, expiry_month, 1, tzinfo=timezone.utc)
    if await redis.ttl(key) < 0:
        await redis.expireat(key, expiry)

    # 总预算也要跟着每笔支出累计，否则只设总预算的用户不会被拦截。
    total_key = budget_total_spent_key(user_id, ledger_id, year, month)
    total_spent = await redis.incrbyfloat(total_key, amount)
    if float(total_spent) < 0:
        await redis.set(total_key, 0, keepttl=True)
    if await redis.ttl(total_key) < 0:
        await redis.expireat(total_key, expiry)

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


async def renew_ledger_lock(
    redis: Redis,
    ledger_id: int,
    request_id: str,
    ttl: int,
) -> bool:
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("expire", KEYS[1], ARGV[2])
    end
    return 0
    """
    renewed = await redis.eval(
        script,
        1,
        f"lock:ledger:{ledger_id}:write",
        request_id,
        ttl,
    )
    return bool(renewed)


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


class LedgerLockBusy(RuntimeError):
    """Another request currently holds the ledger write lock."""


class LedgerLockUnavailable(RuntimeError):
    """Redis is unreachable, so the write cannot be safely serialized."""


@asynccontextmanager
async def ledger_write_lock(
    redis: Redis,
    ledger_id: int,
    ttl: int = 30,
    retry_attempts: int = 5,
):
    request_id = uuid4().hex
    acquired = False
    for attempt in range(retry_attempts):
        try:
            acquired = await acquire_ledger_lock(
                redis, ledger_id, request_id, ttl=ttl
            )
        except RedisError as exc:
            raise LedgerLockUnavailable("账本锁服务暂时不可用") from exc
        if acquired:
            break
        if attempt < retry_attempts - 1:
            await asyncio.sleep(min(0.2, 0.05 * (attempt + 1)))
    if not acquired:
        raise LedgerLockBusy("账本正在被其他请求修改")

    owner_task = asyncio.current_task()

    async def heartbeat() -> None:
        try:
            while True:
                await asyncio.sleep(max(0.1, ttl / 3))
                if not await renew_ledger_lock(redis, ledger_id, request_id, ttl):
                    # 锁已丢失：取消持有者，避免在无锁状态下继续提交。
                    if owner_task is not None:
                        owner_task.cancel()
                    return
        except asyncio.CancelledError:
            raise
        except Exception:
            if owner_task is not None:
                owner_task.cancel()
            return

    renewal_task = asyncio.create_task(heartbeat())
    try:
        yield
    finally:
        renewal_task.cancel()
        with suppress(asyncio.CancelledError):
            await renewal_task
        try:
            await release_ledger_lock(redis, ledger_id, request_id)
        except Exception:
            # TTL will reclaim the lock; release failure must not hide the write result.
            pass


async def close_redis() -> None:
    await pool.disconnect()

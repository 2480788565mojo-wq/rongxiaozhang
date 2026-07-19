import asyncio
import json
import logging
from contextlib import suppress
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.api.v1.sse import publish_user_event
from app.core.database import async_session
from app.core.redis import get_redis
from app.models import ReportType
from app.services.insight_service import INSIGHT_QUEUE, generate_insight_report


logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


async def process_insight_job(redis: Redis, raw_job: str) -> None:
    job: dict[str, Any] = json.loads(raw_job)
    user_id = int(job["user_id"])
    ledger_id = int(job["ledger_id"])
    report_type = ReportType(job["report_type"])
    try:
        async with async_session() as db:
            insight = await generate_insight_report(
                db,
                user_id=user_id,
                ledger_id=ledger_id,
                report_type=report_type,
            )
            await db.commit()
            insight_id = insight.id
        await publish_user_event(
            redis,
            user_id,
            "insight_ready",
            {"insight_id": insight_id, "ledger_id": ledger_id},
        )
    except asyncio.CancelledError:
        await redis.lpush(INSIGHT_QUEUE, raw_job)
        raise
    except Exception as exc:
        attempts = int(job.get("attempts", 0)) + 1
        logger.exception("洞察任务处理失败 job_id=%s", job.get("job_id"))
        if attempts < MAX_ATTEMPTS:
            job["attempts"] = attempts
            await redis.lpush(INSIGHT_QUEUE, json.dumps(job, ensure_ascii=False))
        else:
            await publish_user_event(
                redis,
                user_id,
                "insight_failed",
                {"message": "洞察报告生成失败，请稍后重试", "detail": str(exc)},
            )


async def run_insight_worker(redis: Redis | None = None) -> None:
    client = redis or await get_redis()
    while True:
        try:
            item = await client.blpop(INSIGHT_QUEUE, timeout=5)
            if item is not None:
                await process_insight_job(client, item[1])
        except asyncio.CancelledError:
            raise
        except RedisTimeoutError:
            # Redis 5 may close a blocking read at the same moment as the
            # BLPOP timeout. An empty queue is expected and not an outage.
            continue
        except Exception:
            logger.exception("洞察队列暂时不可用")
            await asyncio.sleep(2)


def main() -> None:
    with suppress(KeyboardInterrupt):
        asyncio.run(run_insight_worker())

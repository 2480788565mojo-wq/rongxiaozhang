import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.api.deps import CurrentUser, RedisClient
from app.config import get_settings
from app.core.rate_limit import (
    acquire_connection_slot,
    release_connection_slot,
    touch_connection_slot,
)

router = APIRouter()
settings = get_settings()


async def publish_user_event(
    redis: Redis,
    user_id: int,
    event: str,
    data: dict[str, Any],
) -> None:
    payload = json.dumps(
        {"event": event, "data": data},
        ensure_ascii=False,
        default=str,
    )
    await redis.publish(f"sse:user:{user_id}", payload)


@router.get("/subscribe")
async def sse_subscribe(
    user: CurrentUser,
    redis: RedisClient,
) -> StreamingResponse:
    channel = f"sse:user:{user.id}"
    slot_namespace = f"user:{user.id}:sse"
    connection_id = uuid.uuid4().hex
    try:
        acquired = await acquire_connection_slot(
            redis,
            slot_namespace,
            connection_id,
            now=time.time(),
            limit=settings.SSE_CONNECTION_LIMIT_PER_USER,
        )
    except RedisError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "实时通知服务暂时不可用",
        ) from exc
    if not acquired:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "实时连接数量已达上限，请关闭其他页面后重试",
            headers={"Retry-After": "30"},
        )

    async def event_stream() -> AsyncIterator[str]:
        pubsub = redis.pubsub()
        try:
            await pubsub.subscribe(channel)
            yield "event: connected\ndata: {}\n\n"
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=15,
                )
                active = await touch_connection_slot(
                    redis,
                    slot_namespace,
                    connection_id,
                    now=time.time(),
                )
                if not active:
                    return
                if message is None:
                    yield ": heartbeat\n\n"
                    continue
                yield f"data: {message['data']}\n\n"
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            finally:
                try:
                    await release_connection_slot(
                        redis,
                        slot_namespace,
                        connection_id,
                    )
                except RedisError:
                    pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

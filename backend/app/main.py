import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.agents.graph import run_transaction_session_cleanup
from app.config import get_settings
from app.core.database import close_db, init_db
from app.core.redis import close_redis
from app.workers.insight_worker import run_insight_worker


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db()
    worker_task = None
    session_cleanup_task = asyncio.create_task(
        run_transaction_session_cleanup(),
        name="agent-session-cleanup",
    )
    if settings.INSIGHT_WORKER_ENABLED:
        worker_task = asyncio.create_task(
            run_insight_worker(),
            name="insight-worker",
        )
    try:
        yield
    finally:
        if worker_task is not None:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task
        session_cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await session_cleanup_task
        await close_redis()
        await close_db()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version="2.0.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials="*" not in settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()

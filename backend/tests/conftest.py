import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("JWT_SECRET", "unit-test-secret-with-at-least-32-characters")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ENABLE_DEV_LOGIN", "false")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("WECHAT_SECRET", "unit-test-wechat-secret")
# Unit tests must stay deterministic and must never spend real AI credits,
# even when the developer has configured keys in backend/.env.
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["QWEN_API_KEY"] = ""


@pytest.fixture
def transaction_state() -> dict:
    from app.agents.state import new_transaction_state

    return new_transaction_state(
        raw_input="午饭68块",
        user_id=1,
        ledger_id=1,
        session_id="test-session",
    )


@pytest.fixture
async def db_session() -> AsyncSession:
    from app.models import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()

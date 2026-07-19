from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models import Bill, Budget
from app.schemas.budget import BudgetSet
from app.services.bill_service import create_bill_from_parsed
from app.services.budget_service import set_budget


@pytest.mark.asyncio
async def test_bill_stays_in_database_when_budget_cache_is_unavailable(db_session):
    redis = AsyncMock()
    redis.incrbyfloat.side_effect = RuntimeError("redis unavailable")

    bill = await create_bill_from_parsed(
        db_session,
        redis,
        user_id=1,
        ledger_id=1,
        parsed={
            "type": "expense",
            "amount": 68,
            "category": "餐饮美食",
            "bill_date": "2026-07-15",
        },
        raw_input="午饭68块",
        confirmation_session_id="session-1",
    )
    await db_session.commit()

    stored = await db_session.scalar(select(Bill).where(Bill.id == bill.id))
    assert stored is not None
    assert stored.confirmation_session_id == "session-1"


@pytest.mark.asyncio
async def test_budget_stays_in_database_when_cache_sync_is_unavailable(db_session):
    redis = AsyncMock()
    redis.set.side_effect = RuntimeError("redis unavailable")
    payload = BudgetSet(
        ledger_id=1,
        year=2026,
        month=7,
        total_budget=5000,
        category_budgets={"餐饮美食": 1000},
    )

    budget = await set_budget(db_session, redis, user_id=1, payload=payload)
    await db_session.commit()

    stored = await db_session.scalar(select(Budget).where(Budget.id == budget.id))
    assert stored is not None
    assert stored.category_budgets == {"餐饮美食": 1000.0}

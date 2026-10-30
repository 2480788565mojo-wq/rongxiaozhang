from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.core.redis import (
    budget_limit_key,
    budget_total_limit_key,
    budget_total_spent_key,
)
from app.models import Bill, BillType, Budget
from app.schemas.budget import BudgetSet
from app.services.budget_service import get_budget_statuses, set_budget


@pytest.mark.asyncio
async def test_get_budget_statuses_reports_total_budget(db_session):
    db_session.add(
        Budget(
            user_id=1,
            ledger_id=9,
            year=2026,
            month=7,
            total_budget=1000,
            category_budgets={},
        )
    )
    db_session.add_all(
        [
            Bill(
                ledger_id=9,
                creator_id=1,
                type=BillType.EXPENSE,
                amount=500,
                category="餐饮美食",
                bill_date=date(2026, 7, 3),
            ),
            Bill(
                ledger_id=9,
                creator_id=1,
                type=BillType.EXPENSE,
                amount=350,
                category="交通出行",
                bill_date=date(2026, 7, 8),
            ),
            # 收入不计入总预算支出
            Bill(
                ledger_id=9,
                creator_id=1,
                type=BillType.INCOME,
                amount=999,
                category="工资",
                bill_date=date(2026, 7, 10),
            ),
            # 其它月份不计入本月总预算支出
            Bill(
                ledger_id=9,
                creator_id=1,
                type=BillType.EXPENSE,
                amount=999,
                category="餐饮美食",
                bill_date=date(2026, 6, 30),
            ),
        ]
    )
    await db_session.flush()

    redis = AsyncMock()
    statuses = await get_budget_statuses(
        db_session,
        redis,
        user_id=1,
        ledger_id=9,
        year=2026,
        month=7,
    )

    assert len(statuses) == 1
    status = statuses[0]
    assert status.category == "总预算"
    assert status.kind == "total"
    assert status.spent == 850
    assert status.budget == 1000
    assert status.remaining == 150
    assert status.percentage == 85
    assert status.risk_level == "warning"

    # 总预算状态同时刷新了 Redis 总预算键，guardian 才能读到同一份数据。
    cached = {call.args[0]: call.args[1] for call in redis.set.await_args_list}
    assert cached[budget_total_limit_key(1, 9, 2026, 7)] == 1000
    assert cached[budget_total_spent_key(1, 9, 2026, 7)] == 850
    total_spent_call = next(
        call
        for call in redis.set.await_args_list
        if call.args[0] == budget_total_spent_key(1, 9, 2026, 7)
    )
    assert total_spent_call.kwargs.get("nx") is True


@pytest.mark.asyncio
async def test_set_budget_caches_total_budget_keys(db_session):
    redis = AsyncMock()
    payload = BudgetSet(
        ledger_id=1,
        year=2026,
        month=7,
        total_budget=1000,
        category_budgets={"餐饮美食": 500},
    )

    await set_budget(db_session, redis, user_id=1, payload=payload)

    cached = {call.args[0]: call.args[1] for call in redis.set.await_args_list}
    assert cached[budget_limit_key(1, 1, 2026, 7, "餐饮美食")] == 500
    assert cached[budget_total_limit_key(1, 1, 2026, 7)] == 1000
    assert cached[budget_total_spent_key(1, 1, 2026, 7)] == 0.0


@pytest.mark.asyncio
async def test_set_budget_clears_total_budget_keys_when_disabled(db_session):
    redis = AsyncMock()
    payload = BudgetSet(
        ledger_id=1,
        year=2026,
        month=7,
        total_budget=None,
        category_budgets={"餐饮美食": 500},
    )

    await set_budget(db_session, redis, user_id=1, payload=payload)

    deleted = {key for call in redis.delete.await_args_list for key in call.args}
    assert budget_total_limit_key(1, 1, 2026, 7) in deleted
    assert budget_total_spent_key(1, 1, 2026, 7) in deleted

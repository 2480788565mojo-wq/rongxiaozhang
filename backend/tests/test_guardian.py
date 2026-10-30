from unittest.mock import AsyncMock

import pytest

import app.agents.guardian as guardian
from app.core.redis import (
    budget_limit_key,
    budget_total_limit_key,
    budget_total_spent_key,
    incr_budget_spent,
)
from app.schemas.budget import BudgetSet
from app.services.budget_service import set_budget


def expense_state(amount: float = 100) -> dict:
    return {
        "user_id": 1,
        "ledger_id": 9,
        "parsed": {
            "type": "expense",
            "amount": amount,
            "category": "餐饮美食",
            "bill_date": "2026-07-15",
        },
    }


def expense_item(amount: float, category: str = "餐饮美食") -> dict:
    return {
        "type": "expense",
        "amount": amount,
        "category": category,
        "bill_date": "2026-07-15",
    }


def items_state(*items: dict) -> dict:
    return {"user_id": 1, "ledger_id": 9, "parsed_items": list(items)}


def budget_double(
    category_budgets: dict | None = None,
    total_budget: float | None = None,
):
    """Budget 测试替身：显式声明 total_budget，避免误触发总预算分支。"""
    return type(
        "Budget",
        (),
        {
            "category_budgets": category_budgets or {},
            "total_budget": total_budget,
        },
    )()


def stub_redis(monkeypatch, *, category_limit, total_limit=None, total_spent=None):
    """Redis 必须按 key 返回不同值：分类额度键和总预算键是两类键。"""
    values = {
        budget_limit_key(1, 9, 2026, 7, "餐饮美食"): category_limit,
        budget_total_limit_key(1, 9, 2026, 7): total_limit,
        budget_total_spent_key(1, 9, 2026, 7): total_spent,
    }

    async def fake_get(key):
        return values.get(key)

    redis = AsyncMock()
    redis.get.side_effect = fake_get
    monkeypatch.setattr(guardian, "get_redis", AsyncMock(return_value=redis))
    return redis


class FakeRedis:
    """只实现预算热路径用到的命令，行为对齐 decode_responses=True 的 Redis。"""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, **kwargs):
        self.values[key] = str(value)
        return True

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)
        return len(keys)

    async def incrbyfloat(self, key, amount):
        current = float(self.values.get(key, 0)) + float(amount)
        self.values[key] = str(current)
        return current

    async def ttl(self, key):
        return -1

    async def expireat(self, key, when):
        return True

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_guardian_skips_income():
    state = expense_state()
    state["parsed"]["type"] = "income"

    result = await guardian.guardian_node(state)

    assert result["risk_level"] == "safe"
    assert result["budget_check"] is None


async def run_guardian(
    monkeypatch,
    spent: float,
    limit: str | None,
    amount=100,
    *,
    total_limit: str | None = None,
    total_spent: str | None = None,
):
    stub_redis(
        monkeypatch,
        category_limit=limit,
        total_limit=total_limit,
        total_spent=total_spent,
    )
    monkeypatch.setattr(
        guardian,
        "get_budget_spent",
        AsyncMock(return_value=spent),
    )
    return await guardian.guardian_node(expense_state(amount))


@pytest.mark.asyncio
async def test_guardian_allows_category_without_budget(monkeypatch):
    result = await run_guardian(monkeypatch, spent=500, limit=None)

    assert result["risk_level"] == "safe"
    assert result["budget_check"] is None


@pytest.mark.asyncio
async def test_guardian_marks_safe_budget(monkeypatch):
    result = await run_guardian(monkeypatch, spent=300, limit="1000")

    assert result["risk_level"] == "safe"
    assert result["budget_check"]["percentage"] == 40


@pytest.mark.asyncio
async def test_guardian_warns_at_eighty_percent(monkeypatch):
    result = await run_guardian(monkeypatch, spent=750, limit="1000")

    assert result["risk_level"] == "warning"
    assert result["budget_check"]["percentage"] == 85


@pytest.mark.asyncio
async def test_guardian_blocks_at_full_budget(monkeypatch):
    result = await run_guardian(monkeypatch, spent=950, limit="1000")

    assert result["risk_level"] == "blocked"
    assert result["budget_check"]["remaining"] == -50


@pytest.mark.asyncio
async def test_guardian_reads_total_budget_from_redis(monkeypatch):
    result = await run_guardian(
        monkeypatch,
        spent=750,
        limit=None,
        total_limit="1000",
        total_spent="750",
    )

    assert result["risk_level"] == "warning"
    check = result["budget_check"]
    assert check["category"] == "总预算"
    assert check["kind"] == "total"
    assert check["spent"] == 750
    assert check["projected_spent"] == 850
    assert check["percentage"] == 85
    assert len(result["budget_checks"]) == 1


@pytest.mark.asyncio
async def test_guardian_checks_each_bill_and_uses_strictest_risk(monkeypatch):
    budget = budget_double(
        category_budgets={"餐饮美食": 1000, "交通出行": 100},
        total_budget=None,
    )
    monkeypatch.setattr(guardian, "get_budget", AsyncMock(return_value=budget))
    monkeypatch.setattr(
        guardian,
        "category_spending",
        AsyncMock(return_value={"餐饮美食": 100, "交通出行": 90}),
    )
    state = items_state(
        expense_item(100, "餐饮美食"),
        expense_item(20, "交通出行"),
    )

    result = await guardian.guardian_budget_node(state, db=AsyncMock())

    assert len(result["budget_checks"]) == 2
    assert result["risk_level"] == "blocked"
    assert result["budget_check"]["category"] == "交通出行"
    assert result["budget_checks"][1]["item_index"] == 1


@pytest.mark.asyncio
async def test_guardian_accumulates_same_batch_spending(monkeypatch):
    budget = budget_double(category_budgets={"餐饮美食": 100}, total_budget=None)
    monkeypatch.setattr(guardian, "get_budget", AsyncMock(return_value=budget))
    monkeypatch.setattr(
        guardian,
        "category_spending",
        AsyncMock(return_value={"餐饮美食": 0}),
    )
    state = items_state(expense_item(60), expense_item(60))

    result = await guardian.guardian_budget_node(state, db=AsyncMock())

    assert result["budget_checks"][0]["risk_level"] == "safe"
    assert result["budget_checks"][1]["risk_level"] == "blocked"
    assert result["budget_checks"][1]["projected_spent"] == 120
    assert result["risk_level"] == "blocked"
    assert result["budget_check"]["item_index"] == 1
    # 同一个月份只查一次预算和支出
    assert guardian.get_budget.await_count == 1
    assert guardian.category_spending.await_count == 1


@pytest.mark.asyncio
async def test_guardian_uses_database_as_source_of_truth(monkeypatch):
    budget = budget_double(category_budgets={"餐饮美食": 1000}, total_budget=None)
    monkeypatch.setattr(guardian, "get_budget", AsyncMock(return_value=budget))
    monkeypatch.setattr(
        guardian,
        "category_spending",
        AsyncMock(return_value={"餐饮美食": 750}),
    )
    get_redis = AsyncMock()
    monkeypatch.setattr(guardian, "get_redis", get_redis)

    result = await guardian.guardian_node(expense_state(), db=AsyncMock())

    assert result["risk_level"] == "warning"
    assert result["budget_check"]["percentage"] == 85
    get_redis.assert_not_awaited()


@pytest.mark.asyncio
async def test_guardian_warns_from_total_budget_in_database(monkeypatch):
    budget = budget_double(total_budget=1000)
    monkeypatch.setattr(guardian, "get_budget", AsyncMock(return_value=budget))
    monkeypatch.setattr(
        guardian,
        "category_spending",
        AsyncMock(return_value={"餐饮美食": 750}),
    )
    get_redis = AsyncMock()
    monkeypatch.setattr(guardian, "get_redis", get_redis)

    result = await guardian.guardian_node(expense_state(), db=AsyncMock())

    assert result["risk_level"] == "warning"
    check = result["budget_check"]
    assert check["category"] == "总预算"
    assert check["kind"] == "total"
    assert check["spent"] == 750
    assert check["projected_spent"] == 850
    assert check["remaining"] == 150
    assert check["percentage"] == 85
    assert len(result["budget_checks"]) == 1
    get_redis.assert_not_awaited()


@pytest.mark.asyncio
async def test_guardian_blocks_from_total_budget_in_database(monkeypatch):
    budget = budget_double(
        category_budgets={"餐饮美食": 5000},
        total_budget=1000,
    )
    monkeypatch.setattr(guardian, "get_budget", AsyncMock(return_value=budget))
    monkeypatch.setattr(
        guardian,
        "category_spending",
        AsyncMock(return_value={"餐饮美食": 950}),
    )

    result = await guardian.guardian_budget_node(
        items_state(expense_item(100)),
        db=AsyncMock(),
    )

    assert result["risk_level"] == "blocked"
    category_check, total_check = result["budget_checks"]
    assert category_check["category"] == "餐饮美食"
    assert category_check["risk_level"] == "safe"
    assert total_check["category"] == "总预算"
    assert total_check["risk_level"] == "blocked"
    assert total_check["projected_spent"] == 1050
    assert total_check["remaining"] == -50
    assert total_check["percentage"] == 105
    assert result["budget_check"]["category"] == "总预算"


@pytest.mark.asyncio
async def test_guardian_blocks_total_budget_without_category_budgets(monkeypatch):
    budget = budget_double(total_budget=1000)
    assert budget.category_budgets == {}
    monkeypatch.setattr(guardian, "get_budget", AsyncMock(return_value=budget))
    monkeypatch.setattr(
        guardian,
        "category_spending",
        AsyncMock(return_value={"餐饮美食": 900}),
    )

    result = await guardian.guardian_budget_node(
        items_state(expense_item(100)),
        db=AsyncMock(),
    )

    # 没有任何分类预算时，仍然只凭总预算拦截，且不产生分类检查项。
    assert len(result["budget_checks"]) == 1
    check = result["budget_checks"][0]
    assert check["category"] == "总预算"
    assert check["projected_spent"] == 1000
    assert check["percentage"] == 100
    assert result["risk_level"] == "blocked"
    assert result["budget_check"]["category"] == "总预算"


@pytest.mark.asyncio
async def test_guardian_accumulates_total_budget_in_same_batch(monkeypatch):
    budget = budget_double(total_budget=100)
    monkeypatch.setattr(guardian, "get_budget", AsyncMock(return_value=budget))
    monkeypatch.setattr(
        guardian,
        "category_spending",
        AsyncMock(return_value={}),
    )
    state = items_state(expense_item(60), expense_item(60))

    result = await guardian.guardian_budget_node(state, db=AsyncMock())

    checks = result["budget_checks"]
    assert [check["category"] for check in checks] == ["总预算", "总预算"]
    assert [check["item_index"] for check in checks] == [0, 1]
    assert [check["projected_spent"] for check in checks] == [60, 120]
    assert checks[0]["risk_level"] == "safe"
    assert checks[1]["risk_level"] == "blocked"
    assert result["risk_level"] == "blocked"
    assert result["budget_check"]["item_index"] == 1
    assert guardian.get_budget.await_count == 1
    assert guardian.category_spending.await_count == 1


@pytest.mark.asyncio
async def test_guardian_strictest_risk_wins_when_category_and_total_trigger(monkeypatch):
    budget = budget_double(
        category_budgets={"餐饮美食": 1000},
        total_budget=1000,
    )
    monkeypatch.setattr(guardian, "get_budget", AsyncMock(return_value=budget))
    monkeypatch.setattr(
        guardian,
        "category_spending",
        AsyncMock(return_value={"餐饮美食": 850, "交通出行": 100}),
    )

    result = await guardian.guardian_budget_node(
        items_state(expense_item(100)),
        db=AsyncMock(),
    )

    category_check, total_check = result["budget_checks"]
    assert category_check["category"] == "餐饮美食"
    assert category_check["percentage"] == 95
    assert category_check["risk_level"] == "warning"
    assert total_check["category"] == "总预算"
    assert total_check["percentage"] == 105
    assert total_check["risk_level"] == "blocked"
    assert result["risk_level"] == "blocked"
    assert result["budget_check"] is total_check


@pytest.mark.asyncio
async def test_redis_total_keys_drive_guardian_after_budget_write(
    db_session,
    monkeypatch,
):
    fake_redis = FakeRedis()
    await set_budget(
        db_session,
        fake_redis,
        user_id=1,
        payload=BudgetSet(
            ledger_id=9,
            year=2026,
            month=7,
            total_budget=1000,
            category_budgets={},
        ),
    )
    await incr_budget_spent(fake_redis, 1, 9, 2026, 7, "餐饮美食", 750)
    await incr_budget_spent(fake_redis, 1, 9, 2026, 7, "交通出行", 100)

    assert float(fake_redis.values[budget_total_limit_key(1, 9, 2026, 7)]) == 1000
    assert float(fake_redis.values[budget_total_spent_key(1, 9, 2026, 7)]) == 850

    monkeypatch.setattr(guardian, "get_redis", AsyncMock(return_value=fake_redis))
    result = await guardian.guardian_budget_node(expense_state())

    assert result["risk_level"] == "warning"
    check = result["budget_check"]
    assert check["category"] == "总预算"
    assert check["spent"] == 850
    assert check["projected_spent"] == 950
    assert check["percentage"] == 95
    assert len(result["budget_checks"]) == 1

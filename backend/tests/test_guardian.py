from unittest.mock import AsyncMock

import pytest

import app.agents.guardian as guardian


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


@pytest.mark.asyncio
async def test_guardian_skips_income():
    state = expense_state()
    state["parsed"]["type"] = "income"

    result = await guardian.guardian_node(state)

    assert result["risk_level"] == "safe"
    assert result["budget_check"] is None


async def run_guardian(monkeypatch, spent: float, limit: str | None, amount=100):
    redis = AsyncMock()
    redis.get.return_value = limit
    monkeypatch.setattr(guardian, "get_redis", AsyncMock(return_value=redis))
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
async def test_guardian_uses_database_as_source_of_truth(monkeypatch):
    budget = type("Budget", (), {"category_budgets": {"餐饮美食": 1000}})()
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

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import TransactionState
from app.config import get_settings
from app.core.redis import budget_limit_key, get_budget_spent, get_redis
from app.services.budget_service import category_spending, get_budget


settings = get_settings()


async def guardian_node(
    state: TransactionState,
    db: AsyncSession | None = None,
) -> TransactionState:
    parsed = state.get("parsed") or {}

    if parsed.get("type") != "expense":
        state["risk_level"] = "safe"
        state["budget_check"] = None
        return state

    amount = parsed.get("amount")
    category = parsed.get("category")
    if amount is None or not category:
        state["risk_level"] = "safe"
        state["budget_check"] = None
        return state

    bill_date = date.fromisoformat(parsed.get("bill_date") or date.today().isoformat())
    if db is not None:
        budget = await get_budget(
            db,
            state["user_id"],
            state["ledger_id"],
            bill_date.year,
            bill_date.month,
        )
        raw_limit = budget.category_budgets.get(category) if budget is not None else None
        spending = await category_spending(
            db,
            user_id=state["user_id"],
            ledger_id=state["ledger_id"],
            year=bill_date.year,
            month=bill_date.month,
        )
        spent = spending.get(category, 0.0)
    else:
        redis = await get_redis()
        try:
            spent = await get_budget_spent(
                redis,
                state["user_id"],
                state["ledger_id"],
                bill_date.year,
                bill_date.month,
                category,
            )
            raw_limit = await redis.get(
                budget_limit_key(
                    state["user_id"],
                    state["ledger_id"],
                    bill_date.year,
                    bill_date.month,
                    category,
                )
            )
        finally:
            await redis.aclose()

    limit = float(raw_limit) if raw_limit is not None else 0.0
    if limit <= 0:
        state["risk_level"] = "safe"
        state["budget_check"] = None
        return state

    projected_spent = spent + float(amount)
    ratio = projected_spent / limit
    remaining = limit - projected_spent

    if ratio >= settings.BUDGET_BLOCKED_RATIO:
        risk_level = "blocked"
    elif ratio >= settings.BUDGET_WARNING_RATIO:
        risk_level = "warning"
    else:
        risk_level = "safe"

    state["risk_level"] = risk_level
    state["budget_check"] = {
        "category": category,
        "spent": round(spent, 2),
        "projected_spent": round(projected_spent, 2),
        "budget": round(limit, 2),
        "remaining": round(remaining, 2),
        "percentage": round(ratio * 100, 1),
        "risk_level": risk_level,
    }
    return state

from datetime import date, datetime, timezone
import logging

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.redis import (
    budget_limit_key,
    budget_spent_key,
    budget_total_limit_key,
    budget_total_spent_key,
)
from app.models import Bill, BillType, Budget
from app.schemas.budget import BudgetSet, BudgetStatus


settings = get_settings()
logger = logging.getLogger(__name__)


def risk_level_for_ratio(ratio: float) -> str:
    """预算比例到风险等级的唯一映射，guardian 和状态接口共用。"""
    if ratio >= settings.BUDGET_BLOCKED_RATIO:
        return "blocked"
    if ratio >= settings.BUDGET_WARNING_RATIO:
        return "warning"
    return "safe"


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _redis_expiry(year: int, month: int) -> datetime:
    _, end = _month_bounds(year, month)
    return datetime(end.year, end.month, end.day, tzinfo=timezone.utc)


async def category_spending(
    db: AsyncSession,
    *,
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
) -> dict[str, float]:
    start, end = _month_bounds(year, month)
    result = await db.execute(
        select(Bill.category, func.sum(Bill.amount))
        .where(
            Bill.creator_id == user_id,
            Bill.ledger_id == ledger_id,
            Bill.type == BillType.EXPENSE,
            Bill.bill_date >= start,
            Bill.bill_date < end,
        )
        .group_by(Bill.category)
    )
    return {category: float(amount) for category, amount in result.all()}


async def set_budget(
    db: AsyncSession,
    redis: Redis,
    user_id: int,
    payload: BudgetSet,
) -> Budget:
    result = await db.execute(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.ledger_id == payload.ledger_id,
            Budget.year == payload.year,
            Budget.month == payload.month,
        )
    )
    budget = result.scalar_one_or_none()
    old_categories = set(budget.category_budgets) if budget is not None else set()
    if budget is None:
        budget = Budget(
            user_id=user_id,
            ledger_id=payload.ledger_id,
            year=payload.year,
            month=payload.month,
        )
        db.add(budget)

    budget.total_budget = payload.total_budget
    budget.category_budgets = dict(payload.category_budgets)
    await db.flush()

    spending = await category_spending(
        db,
        user_id=user_id,
        ledger_id=payload.ledger_id,
        year=payload.year,
        month=payload.month,
    )
    try:
        new_categories = set(payload.category_budgets)
        for category in old_categories - new_categories:
            await redis.delete(
                budget_limit_key(
                    user_id,
                    payload.ledger_id,
                    payload.year,
                    payload.month,
                    category,
                )
            )

        expiry = _redis_expiry(payload.year, payload.month)
        for category, limit in payload.category_budgets.items():
            limit_key = budget_limit_key(
                user_id,
                payload.ledger_id,
                payload.year,
                payload.month,
                category,
            )
            spent_key = budget_spent_key(
                user_id,
                payload.ledger_id,
                payload.year,
                payload.month,
                category,
            )
            await redis.set(limit_key, limit)
            await redis.set(spent_key, spending.get(category, 0.0))
            await redis.expireat(limit_key, expiry)
            await redis.expireat(spent_key, expiry)

        total_limit_key = budget_total_limit_key(
            user_id, payload.ledger_id, payload.year, payload.month
        )
        total_spent_key = budget_total_spent_key(
            user_id, payload.ledger_id, payload.year, payload.month
        )
        if payload.total_budget is None:
            await redis.delete(total_limit_key, total_spent_key)
        else:
            await redis.set(total_limit_key, payload.total_budget)
            await redis.set(total_spent_key, sum(spending.values()))
            await redis.expireat(total_limit_key, expiry)
            await redis.expireat(total_spent_key, expiry)
    except Exception:
        logger.warning("预算缓存同步失败，数据库预算仍已保存", exc_info=True)
    return budget


async def get_budget(
    db: AsyncSession,
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
) -> Budget | None:
    result = await db.execute(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.ledger_id == ledger_id,
            Budget.year == year,
            Budget.month == month,
        )
    )
    return result.scalar_one_or_none()


async def get_budget_statuses(
    db: AsyncSession,
    redis: Redis,
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
) -> list[BudgetStatus]:
    budget = await get_budget(db, user_id, ledger_id, year, month)
    if budget is None:
        return []

    spending = await category_spending(
        db,
        user_id=user_id,
        ledger_id=ledger_id,
        year=year,
        month=month,
    )
    statuses: list[BudgetStatus] = []
    expiry = _redis_expiry(year, month)
    total_spent = sum(spending.values())
    if budget.total_budget is not None and float(budget.total_budget) > 0:
        total_limit = float(budget.total_budget)
        total_ratio = total_spent / total_limit
        statuses.append(
            BudgetStatus(
                category="总预算",
                kind="total",
                spent=round(total_spent, 2),
                budget=round(total_limit, 2),
                remaining=round(total_limit - total_spent, 2),
                percentage=round(total_ratio * 100, 1),
                risk_level=risk_level_for_ratio(total_ratio),
            )
        )
        try:
            total_limit_key = budget_total_limit_key(user_id, ledger_id, year, month)
            total_spent_key = budget_total_spent_key(user_id, ledger_id, year, month)
            await redis.set(total_limit_key, total_limit)
            # spent 由账单增量维护；状态刷新只做“缺失初始化”，
            # 不能用 DB 快照覆盖并发期间已经累加的增量。
            await redis.set(total_spent_key, total_spent, nx=True)
            await redis.expireat(total_limit_key, expiry)
            await redis.expireat(total_spent_key, expiry)
        except Exception:
            logger.warning("总预算缓存刷新失败，状态仍由数据库计算", exc_info=True)

    for category, raw_limit in budget.category_budgets.items():
        limit = float(raw_limit)
        spent = spending.get(category, 0.0)
        ratio = spent / limit if limit > 0 else 0.0
        risk_level = risk_level_for_ratio(ratio) if limit > 0 else "safe"

        limit_key = budget_limit_key(user_id, ledger_id, year, month, category)
        spent_key = budget_spent_key(user_id, ledger_id, year, month, category)
        try:
            await redis.set(limit_key, limit)
            await redis.set(spent_key, spent)
            await redis.expireat(limit_key, expiry)
            await redis.expireat(spent_key, expiry)
        except Exception:
            logger.warning("预算缓存刷新失败，状态仍由数据库计算", exc_info=True)
        statuses.append(
            BudgetStatus(
                category=category,
                spent=round(spent, 2),
                budget=round(limit, 2),
                remaining=round(limit - spent, 2),
                percentage=round(ratio * 100, 1),
                risk_level=risk_level,
            )
        )
    return statuses

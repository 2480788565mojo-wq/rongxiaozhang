from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bill, BillType, Budget
from app.schemas.stats import CategoryStat, StatsOverview, TrendPoint


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        return start, date(year + 1, 1, 1)
    return start, date(year, month + 1, 1)


def shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    month_index = year * 12 + (month - 1) + offset
    return month_index // 12, month_index % 12 + 1


async def get_overview(
    db: AsyncSession,
    *,
    user_id: int,
    ledger_id: int,
    year: int,
    month: int,
) -> StatsOverview:
    start, end = month_bounds(year, month)
    result = await db.execute(
        select(Bill.type, func.coalesce(func.sum(Bill.amount), 0))
        .where(
            Bill.ledger_id == ledger_id,
            Bill.bill_date >= start,
            Bill.bill_date < end,
        )
        .group_by(Bill.type)
    )
    totals = {bill_type: float(amount) for bill_type, amount in result.all()}
    income = totals.get(BillType.INCOME, 0.0)
    expense = totals.get(BillType.EXPENSE, 0.0)

    budget_result = await db.execute(
        select(Budget.total_budget).where(
            Budget.user_id == user_id,
            Budget.ledger_id == ledger_id,
            Budget.year == year,
            Budget.month == month,
        )
    )
    total_budget = budget_result.scalar_one_or_none()
    budget_percentage = None
    if total_budget is not None and float(total_budget) > 0:
        budget_percentage = round(expense / float(total_budget) * 100, 1)

    return StatsOverview(
        ledger_id=ledger_id,
        year=year,
        month=month,
        income=round(income, 2),
        expense=round(expense, 2),
        balance=round(income - expense, 2),
        budget_used_percentage=budget_percentage,
    )


async def get_trend(
    db: AsyncSession,
    *,
    ledger_id: int,
    months: int,
    end_year: int,
    end_month: int,
) -> list[TrendPoint]:
    first_year, first_month = shift_month(end_year, end_month, -(months - 1))
    start, _ = month_bounds(first_year, first_month)
    _, end = month_bounds(end_year, end_month)
    result = await db.execute(
        select(
            func.extract("year", Bill.bill_date),
            func.extract("month", Bill.bill_date),
            Bill.type,
            func.sum(Bill.amount),
        )
        .where(
            Bill.ledger_id == ledger_id,
            Bill.bill_date >= start,
            Bill.bill_date < end,
        )
        .group_by(
            func.extract("year", Bill.bill_date),
            func.extract("month", Bill.bill_date),
            Bill.type,
        )
    )
    totals: dict[tuple[int, int], dict[BillType, float]] = {}
    for raw_year, raw_month, bill_type, amount in result.all():
        key = (int(raw_year), int(raw_month))
        totals.setdefault(key, {})[bill_type] = float(amount)

    items: list[TrendPoint] = []
    for offset in range(months):
        year, month = shift_month(first_year, first_month, offset)
        month_totals = totals.get((year, month), {})
        items.append(
            TrendPoint(
                period=f"{year:04d}-{month:02d}",
                income=round(month_totals.get(BillType.INCOME, 0.0), 2),
                expense=round(month_totals.get(BillType.EXPENSE, 0.0), 2),
            )
        )
    return items


async def get_category_stats(
    db: AsyncSession,
    *,
    ledger_id: int,
    year: int,
    month: int,
) -> tuple[list[CategoryStat], float]:
    start, end = month_bounds(year, month)
    result = await db.execute(
        select(Bill.category, func.sum(Bill.amount))
        .where(
            Bill.ledger_id == ledger_id,
            Bill.type == BillType.EXPENSE,
            Bill.bill_date >= start,
            Bill.bill_date < end,
        )
        .group_by(Bill.category)
        .order_by(func.sum(Bill.amount).desc())
    )
    rows = [(category, float(amount)) for category, amount in result.all()]
    total = sum(amount for _, amount in rows)
    items = [
        CategoryStat(
            category=category,
            amount=round(amount, 2),
            percentage=round(amount / total * 100, 1) if total > 0 else 0.0,
        )
        for category, amount in rows
    ]
    return items, round(total, 2)

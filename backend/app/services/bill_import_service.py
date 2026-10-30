"""Write one bounded Excel batch without repeating per-row database work."""

import logging
from collections import defaultdict
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import case, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import incr_budget_spent
from app.models import Account, Bill, BillType
from app.schemas.bill import BillImportItem, BillImportResultItem
from app.services.account_service import account_balance_delta


logger = logging.getLogger(__name__)
BudgetDeltas = dict[tuple[int, int, str], Decimal]


def _matches_import(bill: Bill, item: BillImportItem) -> bool:
    """A retry key may acknowledge its original row, never a changed row."""
    return (
        bill.type == item.type
        and bill.amount == Decimal(str(item.amount))
        and all(
            getattr(bill, field) == getattr(item, field)
            for field in ("category", "subcategory", "account", "note", "bill_date")
        )
    )


async def prepare_bill_import(
    db: AsyncSession,
    *,
    user_id: int,
    ledger_id: int,
    items: list[BillImportItem],
) -> tuple[list[BillImportResultItem], BudgetDeltas]:
    """Caller holds the user billing lock and commits this batch once.

    Rows and account changes share one transaction. Budget-cache changes are
    returned for application only after the database commit has succeeded.
    """
    keys = [item.import_key for item in items]
    existing_result = await db.execute(
        select(Bill)
        .where(
            Bill.creator_id == user_id,
            Bill.ledger_id == ledger_id,
            Bill.confirmation_session_id.in_(keys),
        )
        .order_by(Bill.id)
        .with_for_update()
    )
    existing = {
        bill.confirmation_session_id: bill
        for bill in existing_result.scalars().all()
    }
    for item in items:
        bill = existing.get(item.import_key)
        if bill is not None and not _matches_import(bill, item):
            raise ValueError("导入编号对应的账单内容已改变，请核对后重新选择文件")

    new_items = [item for item in items if item.import_key not in existing]
    account_deltas: dict[str, Decimal] = defaultdict(Decimal)
    budget_deltas: BudgetDeltas = defaultdict(Decimal)
    values = []
    for item in new_items:
        amount = Decimal(str(item.amount))
        bill_type = BillType(item.type)
        values.append({
            "ledger_id": ledger_id,
            "creator_id": user_id,
            "type": bill_type,
            "amount": amount,
            "category": item.category,
            "subcategory": item.subcategory,
            "account": item.account,
            "note": item.note,
            "bill_date": item.bill_date,
            "raw_input": "",
            "ai_parsed": False,
            "confirmation_session_id": item.import_key,
        })
        if item.account:
            account_deltas[item.account] += account_balance_delta(bill_type, amount)
        if bill_type == BillType.EXPENSE:
            budget_deltas[(item.bill_date.year, item.bill_date.month, item.category)] += amount

    if values:
        # All nullable fields are present so SQLAlchemy can send one bulk insert.
        await db.execute(insert(Bill).execution_options(render_nulls=True), values)

    if account_deltas:
        # Compare inside the database: its collation may treat ICBC and icbc
        # as one account. Add every matching alias, rather than CASE's first match.
        delta_expression = sum(
            case((Account.name == name, delta), else_=Decimal("0.00"))
            for name, delta in account_deltas.items()
        )
        accounts = await db.execute(
            select(Account, delta_expression.label("import_delta"))
            .where(
                Account.user_id == user_id,
                Account.ledger_id == ledger_id,
                Account.name.in_(account_deltas),
            )
            .order_by(Account.id)
            .with_for_update()
        )
        # Match manual entry semantics: missing/deleted accounts stay unlinked.
        for account, delta in accounts.all():
            account.balance += delta
        await db.flush()

    # Locking reads can see a newer commit than MySQL's transaction snapshot.
    # Reuse their IDs; a later ordinary read must only fetch our own new rows.
    ids = {key: bill.id for key, bill in existing.items()}
    if new_items:
        saved = await db.execute(
            select(Bill.confirmation_session_id, Bill.id).where(
                Bill.creator_id == user_id,
                Bill.ledger_id == ledger_id,
                Bill.confirmation_session_id.in_([item.import_key for item in new_items]),
            )
        )
        ids.update(saved.all())
    return [
        BillImportResultItem(
            import_key=item.import_key,
            bill_id=ids[item.import_key],
            created=item.import_key not in existing,
        )
        for item in items
    ], dict(budget_deltas)


async def update_import_budget_cache(
    redis: Redis,
    *,
    user_id: int,
    ledger_id: int,
    deltas: BudgetDeltas,
) -> None:
    """Cache failure cannot turn an already committed batch into a failed one."""
    for (year, month, category), amount in deltas.items():
        try:
            await incr_budget_spent(
                redis, user_id, ledger_id, year, month, category, float(amount)
            )
        except Exception:
            logger.warning("导入账单已保存，预算缓存更新失败；统计仍以数据库为准", exc_info=True)
